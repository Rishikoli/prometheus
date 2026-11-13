"""Browser check of the page: clicks, keyboard, Play, slider, modes, offline, console errors.

Not part of pytest (it needs a browser). Usage, with `prometheus serve data/prometheus.rl --weights-from results/backtest.json` running:
    pip install playwright && python scripts/ui_check.py [chrome path]
It expects the real PatentsView store (123 fields) on http://127.0.0.1:8765/.
"""
import json, sys, time
from playwright.sync_api import sync_playwright
BASE="http://127.0.0.1:8765/"
res=[]; 
def ok(name,cond,extra=""):
    res.append((name,bool(cond),extra)); print(("PASS " if cond else "FAIL ")+name+(" | "+str(extra) if extra else ""))
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=(sys.argv[1] if len(sys.argv)>1 else "/usr/bin/google-chrome"),headless=True,args=["--no-sandbox"])
    ctx=b.new_context(viewport={"width":1440,"height":900})
    pg=ctx.new_page()
    errs=[];reqs=[]
    pg.on("console",lambda m: errs.append(m.text) if m.type=="error" else None)
    pg.on("pageerror",lambda e: errs.append("PAGEERROR "+str(e)))
    pg.on("request",lambda r: reqs.append(r.url))
    pg.goto(BASE); pg.wait_for_selector(".leaf",timeout=60000); pg.wait_for_function("document.querySelector('#year').value=='2005' && document.querySelectorAll('#note li').length>0",timeout=60000)
    ok("123 leaves drawn", pg.locator(".leaf").count()==123, pg.locator(".leaf").count())
    ok("default year 2005", pg.input_value("#year")=="2005")
    ok("NO-GO sentence visible", "Prediction check failed" in pg.inner_text("#verdict"))
    ok("fonts loaded locally", pg.evaluate("document.fonts.check('600 28px Newsreader') && document.fonts.check('400 14px \"Instrument Sans\"')"))
    # keyboard: Tab to the first leaf, Enter selects
    pg.keyboard.press("Tab")
    for _ in range(12):
        if pg.evaluate("document.activeElement && document.activeElement.classList && document.activeElement.classList.contains('leaf')"): break
        pg.keyboard.press("Tab")
    focused=pg.evaluate("document.activeElement.getAttribute('aria-label')")
    ok("Tab reaches a leaf (role=button, labelled)", focused and len(focused)>4, focused)
    code=pg.evaluate("document.activeElement.dataset.c")
    pg.keyboard.press("Enter"); pg.wait_for_timeout(600)
    ok("Enter selects the field", code in pg.inner_text("#note h2"), pg.inner_text("#note h2"))
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    ok("Esc clears selection", pg.inner_text("#note h2")=="Combinations")
    # click a leaf with the mouse
    pg.locator(".leaf").nth(10).click(force=True); pg.wait_for_timeout(600)
    ok("click selects a field", pg.evaluate("S.sel && S.sel.type==='field'"))
    # likely-next row -> pair
    pg.locator("#note .row").first.click(); pg.wait_for_timeout(1500)
    ok("row selects a pair and loads evidence", pg.evaluate("S.sel.type==='pair' && !!EV"), pg.inner_text("#note h2"))
    ok("evidence rings drawn on the tree", pg.locator("#evrings circle").count()>0, pg.locator("#evrings circle").count())
    # click on a gap arc on the canvas
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    pt=pg.evaluate("""()=>{const g=hit[0];const svg=document.querySelector('#sv g');const path=document.createElementNS('http://www.w3.org/2000/svg','path');
      path.setAttribute('d',lineStr(arc(g.a,g.b).pts));svg.appendChild(path);const L=path.getTotalLength(),q=path.getPointAtLength(L/2);path.remove();
      const r=document.querySelector('#cv').getBoundingClientRect();return {x:r.left+R+q.x,y:r.top+R+q.y,a:g.a,b:g.b}}""")
    pg.mouse.move(pt["x"],pt["y"]); pg.wait_for_timeout(250)
    tip=pg.inner_text("#tip") if pg.is_visible("#tip") else ""
    ok("hovering a gap arc shows 'has not combined'", "has not combined" in tip, tip.replace("\n"," "))
    pg.mouse.click(pt["x"],pt["y"]); pg.wait_for_timeout(1500)
    ok("clicking a gap arc selects that pair", pg.evaluate("S.sel&&S.sel.type==='pair'&&((S.sel.a==='%s'&&S.sel.b==='%s')||(S.sel.a==='%s'&&S.sel.b==='%s'))"%(pt['a'],pt['b'],pt['b'],pt['a'])))
    pg.keyboard.press("Escape")
    # modes
    pg.locator(".leaf").nth(20).click(force=True); pg.wait_for_timeout(500)
    pg.click("[data-mode=deps]"); pg.wait_for_timeout(1500)
    ok("Dependencies mode loads reach", pg.evaluate("!!REACH && Object.keys(REACH.ancestors).length>=0"), pg.inner_text("#note h3").split("\n")[0] if pg.locator("#note h3").count() else "")
    pg.click("[data-mode=breaks]"); pg.wait_for_timeout(1500)
    ok("What breaks mode loads exposure with support", pg.evaluate("!!KO && Object.keys(KO.support).length>0"))
    pg.click("[data-mode=combos]"); pg.wait_for_timeout(500)
    # scores
    pg.click("[data-score=size]"); pg.wait_for_timeout(300); a=pg.inner_text("#note")
    pg.click("[data-score=beyond]"); pg.wait_for_timeout(300); b2=pg.inner_text("#note")
    ok("changing the score re-ranks the note", a!=b2)
    # slider keys
    pg.focus("#year"); y0=int(pg.input_value("#year")); pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(1200)
    ok("slider ArrowRight advances one year", int(pg.input_value("#year"))==y0+1 and pg.text_content("#yr")==str(y0+1) or pg.evaluate("S.year")==y0+1, (y0,pg.evaluate("S.year")))
    # happened toggle range
    pg.evaluate("loadYear(2014)"); pg.wait_for_timeout(1500)
    ok("'Show what happened' enabled at 2014", not pg.is_disabled("#happened"))
    pg.check("#happened"); pg.wait_for_timeout(1500)
    ok("happened draws truth for gaps", pg.evaluate("S.happened && !!FUT && drawnGaps().some(g=>truth(g)!==null)"))
    pg.evaluate("loadYear(2015)"); pg.wait_for_timeout(1500)
    ok("disabled after 2014 with tooltip", pg.is_disabled("#happened") and "ten years" in (pg.get_attribute("#hlab","title") or "") and not pg.evaluate("S.happened"))
    # play
    pg.evaluate("loadYear(2005)"); pg.wait_for_timeout(800)
    pg.click("#play"); pg.wait_for_timeout(1800); y1=pg.evaluate("S.year"); pg.click("#play")
    ok("Play advances years", y1>=2007, y1)
    # details
    pg.click("#det"); pg.wait_for_timeout(300)
    ok("Details panel opens with table and chart", pg.is_visible("#check") and pg.locator("#check table tbody tr").count()==3 and pg.locator("#check svg circle").count()>=12, pg.locator("#check svg circle").count())
    # network: only localhost
    ext=[u for u in reqs if not u.startswith(BASE) and not u.startswith("data:")]
    ok("no request leaves localhost (works offline)", len(ext)==0, ext[:3])
    ok("no console errors", len(errs)==0, errs[:3])
    # the tree page links to the matrix, keeping the year and score
    href=pg.get_attribute("#tomatrix","href")
    ok("tree page links to the matrix with year and score", href.startswith("/matrix#year=") and "score=" in href, href)
    # ---- matrix view ----
    mp=ctx.new_page(); merrs=[]; mreqs=[]
    mp.on("console",lambda m: merrs.append(m.text) if m.type=="error" else None)
    mp.on("pageerror",lambda e: merrs.append("PAGEERROR "+str(e)))
    mp.on("request",lambda r: mreqs.append(r.url))
    mp.goto(BASE+"matrix#year=2005"); mp.wait_for_selector("#cv",timeout=60000)
    mp.wait_for_function("document.querySelectorAll('#note li').length>0",timeout=60000)
    ok("matrix: page loads at 2005 with top gaps", mp.evaluate("S.year===2005 && ST.gaps.length>100"), mp.evaluate("ST.gaps.length"))
    ok("matrix: NO-GO sentence visible", "Prediction check failed" in mp.inner_text("#verdict"))
    ok("matrix: link back to the tree keeps year", mp.get_attribute("#totree","href").startswith("/#year=2005"), mp.get_attribute("#totree","href"))
    cpt=mp.evaluate("""()=>{const g=topGaps()[0],r=document.querySelector('#cv').getBoundingClientRect();
      return {x:r.left+(idx[g.a]+.5)*cell,y:r.top+(idx[g.b]+.5)*cell,a:g.a,b:g.b}}""")
    mp.mouse.move(cpt["x"],cpt["y"]); mp.wait_for_timeout(250)
    tip=mp.inner_text("#tip") if mp.is_visible("#tip") else ""
    ok("matrix: hovering a gap cell shows its ranks", "has not combined" in tip and "graph #" in tip, tip.replace("\n"," "))
    mp.mouse.click(cpt["x"],cpt["y"]); mp.wait_for_timeout(1500)
    ok("matrix: clicking a gap cell selects the pair and loads evidence", mp.evaluate("!!S.sel && !!EV"), mp.inner_text("#note h2"))
    mp.keyboard.press("Escape"); mp.wait_for_timeout(300)
    ok("matrix: Esc clears", mp.inner_text("#note h2")=="Matrix")
    a=mp.inner_text("#note"); mp.click("[data-score=size]"); mp.wait_for_timeout(300); b2=mp.inner_text("#note")
    ok("matrix: score toggle re-ranks the list", a!=b2)
    mp.focus("#year"); mp.keyboard.press("ArrowRight"); mp.wait_for_timeout(1200)
    ok("matrix: slider ArrowRight advances a year", mp.evaluate("S.year")==2006, mp.evaluate("S.year"))
    mp.click("#play"); mp.wait_for_timeout(1700); y=mp.evaluate("S.year"); mp.click("#play")
    ok("matrix: Play advances years", y>=2008, y)
    ext=[u for u in mreqs if not u.startswith(BASE) and not u.startswith("data:")]
    ok("matrix: no request leaves localhost", len(ext)==0, ext[:3])
    ok("matrix: no console errors", len(merrs)==0, merrs[:3])
    # reduced motion + resize
    c2=b.new_context(viewport={"width":1280,"height":800},reduced_motion="reduce"); p2=c2.new_page(); e2=[]
    p2.on("pageerror",lambda e: e2.append(str(e))); p2.goto(BASE); p2.wait_for_selector(".leaf",timeout=60000); p2.wait_for_timeout(2500)
    p2.evaluate("loadYear(2006)"); p2.wait_for_timeout(1200)
    ok("reduced motion: page runs, no errors", not e2 and p2.evaluate("REDUCED===true"))
    p2.set_viewport_size({"width":1500,"height":950}); p2.wait_for_timeout(900)
    ok("resize redraws the plate", p2.locator(".leaf").count()==123)
    b.close()
bad=[r for r in res if not r[1]]
print("\n%d checks, %d failed"%(len(res),len(bad)))
sys.exit(1 if bad else 0)
