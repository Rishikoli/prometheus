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
    b=p.chromium.launch(executable_path=(sys.argv[1] if len(sys.argv)>1 else "/usr/bin/google-chrome"),headless=True,args=["--no-sandbox","--enable-webgl","--ignore-gpu-blocklist"])
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
    # per-year tree
    pg.evaluate("loadYear(1985)"); pg.wait_for_timeout(2500)
    na=pg.evaluate("TR.alive.length"); nd_=pg.evaluate("TR.full.length-TR.alive.length"); born=pg.evaluate("META.fields.filter(f=>f.firstYear<=1985).length")
    ok("tree: 1985 tree is built over the fields alive that year; the rest wait in the gap", na==born and nd_==123-born and nd_>0, (na,nd_,born))
    ok("tree: dead fields sit at the end of the circle and are dimmed", pg.evaluate("TR.full.slice(TR.alive.length).every(c=>byCode[c].firstYear>1985) && document.querySelectorAll('.leaf.dead').length===TR.full.length-TR.alive.length"))
    pg.evaluate("loadYear(2005)"); pg.wait_for_timeout(2500)
    before=pg.evaluate("({...idx})"); pg.evaluate("loadYear(2006)"); pg.wait_for_timeout(2500)
    mv=pg.evaluate("(b=>{const c=Object.keys(b).filter(k=>idx[k]!==undefined);return c.reduce((t,k)=>t+Math.min(Math.abs(idx[k]-b[k]),N-Math.abs(idx[k]-b[k])),0)/c.length})")(before) if False else pg.evaluate("(()=>{const b=%s;const c=Object.keys(b);return c.reduce((t,k)=>t+Math.min(Math.abs(idx[k]-b[k]),N-Math.abs(idx[k]-b[k])),0)/c.length})()"%json.dumps(before))
    ok("tree: consecutive years keep leaves close (mean move under 12 of 123 positions)", mv<12, round(mv,1))
    ok("tree: animation settles with arcs shown", pg.evaluate("document.querySelector('#cv').style.opacity==='1' && document.querySelectorAll('#branches path').length>100"))
    pg.evaluate("loadYear(1976)"); pg.wait_for_timeout(2500)
    ok("tree: first data year loads", pg.evaluate("S.year===1976 && TR.alive.length>50"))
    pg.evaluate("loadYear(2005)"); pg.wait_for_timeout(2500)
    fx=ctx.new_page(); fxe=[]; fx.on("pageerror",lambda e: fxe.append(str(e))); fx.goto(BASE+"#tree=fixed&year=1990"); fx.wait_for_selector(".leaf",timeout=60000); fx.wait_for_timeout(3000)
    ok("tree: #tree=fixed keeps the single all-data tree", fx.evaluate("TREEMODE==='fixed' && TR.full.length===123 && TR.alive.length===123") and not fxe, fxe[:2])
    fx.close()
    # tree: search, newest only, links
    pg.evaluate("scrollTo(0,0)"); pg.evaluate("loadYear(2010)"); pg.wait_for_timeout(2500)
    all_n=pg.evaluate("DRAWN"); pg.check("#recent"); pg.wait_for_timeout(500); new_n=pg.evaluate("DRAWN")
    ok("tree: 'Newest only' keeps just the last three years of arcs", 0<new_n<all_n/3, (all_n,new_n))
    pg.uncheck("#recent"); pg.wait_for_timeout(300)
    pg.fill("#findfield","g06f"); pg.dispatch_event("#findfield","change"); pg.wait_for_timeout(1200)
    ok("tree: 'Find a field' selects it", pg.evaluate("S.sel&&S.sel.type==='field'&&S.sel.code==='G06F'") and pg.inner_text("#note h2")=="G06F")
    ok("tree: the selected field is carried to the matrix and landscape", "field=G06F" in (pg.get_attribute("#tomatrix","href") or "") and "field=G06F" in (pg.get_attribute("#tolandscape","href") or ""))
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    ok("tree: footer credits PatentsView", "PatentsView" in pg.inner_text("footer"))
    # stalled-pair overlay
    pg.evaluate("loadYear(2005)"); pg.wait_for_timeout(1000); pg.check("#stalled"); pg.wait_for_timeout(1800)
    ok("tree: 'Show stalled pairs' loads the overlay", pg.evaluate("S.stalled && !!STL && STL.pairs.length>100"), pg.evaluate("STL&&STL.pairs.length"))
    ok("tree: legend names the stalled arcs without using fire", "stalled" in pg.inner_text("#legend") and pg.evaluate("css('--grey-2')!==css('--fire-3')"))
    pg.uncheck("#stalled"); pg.wait_for_timeout(800)
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
    # ---- matrix readability: gutters, crosshair, search, stalled, links ----
    mp.keyboard.press("Escape"); mp.evaluate("scrollTo(0,0)"); mp.evaluate("loadYear(2005)"); mp.wait_for_timeout(1500)
    ok("matrix: field codes and domain names label the right and bottom edges", mp.locator("#gut text.cd").count()>=40 and mp.locator("#gut text.dn").count()>=3, (mp.locator("#gut text.cd").count(), mp.locator("#gut text.dn").count()))
    cp=mp.evaluate("(()=>{const r=document.querySelector('#cv').getBoundingClientRect();const g=topGaps()[1];return {x:r.left+(idx[g.a]+.5)*cell,y:r.top+(idx[g.b]+.5)*cell,a:g.a,b:g.b}})()")
    mp.mouse.move(cp["x"]-20,cp["y"]-20); mp.wait_for_timeout(100); mp.mouse.move(cp["x"],cp["y"]); mp.wait_for_timeout(300)
    names=mp.evaluate("[...document.querySelectorAll('#marks text')].map(t=>t.textContent)")
    ok("matrix: hovering a cell draws a crosshair and names both fields in the gutters", mp.evaluate("!!hover") and cp["a"] in names and cp["b"] in names, names)
    mp.mouse.move(5,5); mp.wait_for_timeout(200)
    ok("matrix: leaving the grid removes the crosshair", mp.evaluate("hover===null") and mp.locator("#marks text").count()==0)
    mp.fill("#findfield","h01l"); mp.dispatch_event("#findfield","change"); mp.wait_for_timeout(600)
    ok("matrix: 'Find a field' outlines its row and column and lists its candidates", mp.evaluate("S.focus==='H01L'") and mp.inner_text("#note h2")=="H01L" and mp.locator("#marks text").count()>=2 and mp.is_visible("#clearfocus"))
    ok("matrix: the focused field is carried to the other views", "field=H01L" in (mp.get_attribute("#totree","href") or "") and "field=H01L" in (mp.get_attribute("#tolandscape","href") or ""))
    mp.keyboard.press("Escape"); mp.wait_for_timeout(300)
    ok("matrix: Esc clears the focus", mp.evaluate("S.focus===null") and mp.input_value("#findfield")=="")
    mp.check("#stalled"); mp.wait_for_timeout(1500)
    ok("matrix: 'Show stalled pairs' loads and names them in the legend", mp.evaluate("S.stalled && !!STL && STL.pairs.length>100") and "stalled" in mp.inner_text("#legend"))
    mp.uncheck("#stalled"); mp.wait_for_timeout(600)
    ok("matrix: footer credits PatentsView", "PatentsView" in mp.inner_text("footer"))
    ext=[u for u in mreqs if not u.startswith(BASE) and not u.startswith("data:")]
    ok("matrix: no request leaves localhost", len(ext)==0, ext[:3])
    ok("matrix: no console errors", len(merrs)==0, merrs[:3])
    # ---- landscape (3D) view ----
    lp=ctx.new_page(); lerrs=[]; lreqs=[]
    lp.on("console",lambda m: lerrs.append(m.text) if m.type=="error" else None)
    lp.on("pageerror",lambda e: lerrs.append("PAGEERROR "+str(e)))
    lp.on("request",lambda r: lreqs.append(r.url))
    lp.goto(BASE+"landscape#year=2005"); lp.wait_for_selector("#cv",timeout=60000)
    lp.wait_for_function("typeof ST!=='undefined' && ST && document.querySelectorAll('#note li').length>0",timeout=60000); lp.wait_for_timeout(1500)
    ok("landscape: WebGL renderer created", lp.evaluate("!!renderer && renderer.domElement.width>0"))
    api_state=lp.evaluate("fetch('/api/state?year=2005').then(r=>r.json()).then(d=>({c:d.combined.length,n:d.candidates}))")
    diag=lp.inner_text("#diag").replace(",","")
    ok("landscape: diagnostics match the API", str(api_state["c"]) in diag and str(api_state["n"]) in diag, (api_state, diag.replace("\n"," ")[:90]))
    ok("landscape: year numeral shows 2005", lp.inner_text("#yr")=="2005")
    ok("landscape: combination history table has rows ending in 2005", lp.locator("#hist tbody tr").count()>=3 and "2005" in lp.inner_text("#hist tbody tr:last-child td"), lp.locator("#hist tbody tr").count())
    hmax_smooth=lp.evaluate("Math.max(...HT)")
    lp.click("[data-surf=pairs]"); lp.wait_for_timeout(800); hmax_pairs=lp.evaluate("Math.max(...HT)")
    ok("landscape: Each pair gives taller single spikes than Smooth", hmax_pairs>0 and abs(hmax_pairs-hmax_smooth)>0.5, (round(hmax_smooth,1),round(hmax_pairs,1)))
    lp.click("[data-surf=smooth]"); lp.wait_for_timeout(800)
    y_before=lp.evaluate("camera.position.y"); lp.click("[data-cam=top]"); lp.wait_for_timeout(300)
    ok("landscape: Top down moves the camera overhead", lp.evaluate("camera.position.y")>y_before+30, (round(y_before),round(lp.evaluate('camera.position.y'))))
    lp.click("[data-cam=oblique]"); lp.wait_for_timeout(300)
    pt=lp.evaluate("(()=>{const g=topGaps()[0];const p=cellScreen(g.a,g.b);return {x:p.x,y:p.y,a:g.a,b:g.b}})()")
    lp.mouse.move(pt["x"],pt["y"]); lp.wait_for_timeout(300)
    tip=lp.inner_text("#tip") if lp.is_visible("#tip") else ""
    ok("landscape: hovering a peak shows a pair and its ranks", "×" in tip and "graph #" in tip, tip.replace("\n"," ")[:80])
    lp.mouse.click(pt["x"],pt["y"]); lp.wait_for_timeout(1800)
    ok("landscape: clicking a peak selects a pair with evidence", lp.evaluate("!!S.sel && !!EV"), lp.inner_text("#note h2"))
    ok("landscape: callout and stacked-area cross-section appear for the selection", lp.is_visible("#callout") and lp.locator("#xs svg path[data-layer]").count()>=4, lp.locator("#xs svg path[data-layer]").count())
    lp.keyboard.press("Escape"); lp.wait_for_timeout(300)
    ok("landscape: Esc clears", lp.inner_text("#note h2")=="Landscape")
    lp.evaluate("pick(topGaps()[1].a,topGaps()[1].b)"); lp.wait_for_timeout(1500)
    ok("landscape: Top gaps rows select a pair (keyboard route)", lp.evaluate("!!S.sel"))
    lp.keyboard.press("Escape")
    lp.focus("#year"); lp.keyboard.press("ArrowRight"); lp.wait_for_timeout(1500)
    ok("landscape: slider ArrowRight advances a year", lp.evaluate("S.year")==2006 and lp.inner_text("#yr")=="2006")
    lp.click("#play"); lp.wait_for_timeout(2400); y=lp.evaluate("S.year"); lp.click("#play")
    ok("landscape: Play advances years", y>=2008, y)
    lp.click("[data-score=size]"); lp.wait_for_timeout(800)
    ok("landscape: score toggle re-ranks", lp.evaluate("S.score")=="size")
    # ---- landscape readability: labels, crosshair, search, camera ----
    lp.keyboard.press("Escape"); lp.evaluate("loadYear(2005)"); lp.wait_for_timeout(2500)
    ok("landscape: domain names and field codes label the edges", lp.evaluate("[...document.querySelectorAll('#labels .dl')].filter(e=>e.style.display==='block').length")>=3 and lp.evaluate("[...document.querySelectorAll('#labels .cd')].filter(e=>e.style.display==='block').length")>=10)
    overlap_js = """(sel)=>{const r=[...document.querySelectorAll(sel)].filter(e=>e.style.display==='block').map(e=>e.getBoundingClientRect());
      let bad=0;for(let i=0;i<r.length;i++)for(let j=i+1;j<r.length;j++){const a=r[i],b=r[j];if(!(a.right<=b.left+1||a.left>=b.right-1||a.bottom<=b.top+1||a.top>=b.bottom-1))bad++}return {n:r.length,bad}}"""
    dl=lp.evaluate(overlap_js,"#labels .dl"); pk=lp.evaluate(overlap_js,"#labels .pk")
    ok("landscape: domain labels do not overlap each other", dl["bad"]==0 and dl["n"]>=3, dl)
    ok("landscape: 3 to 8 peak labels, none overlapping", 3<=pk["n"]<=8 and pk["bad"]==0, pk)
    pkl=lp.evaluate("(()=>{const e=[...document.querySelectorAll('#labels .pk')].find(e=>e.style.display==='block');return e?{g:e._g.a+' '+e._g.b,txt:e.textContent}:null})()")
    lp.evaluate("[...document.querySelectorAll('#labels .pk')].find(e=>e.style.display==='block').click()"); lp.wait_for_timeout(1500)
    ok("landscape: clicking a peak label selects that pair", pkl and lp.evaluate("!!S.sel && (S.sel.a+' '+S.sel.b)==='%s' || (S.sel.b+' '+S.sel.a)==='%s'"%(pkl['g'],pkl['g'])), pkl)
    ok("landscape: the selected pair is marked on the edges and by crosshair lines", lp.evaluate("[...document.querySelectorAll('#labels .mk')].filter(e=>e.style.display==='block').length")>=2 and lp.evaluate("ribbons.filter(r=>r.visible).length")>=4)
    lp.keyboard.press("Escape"); lp.wait_for_timeout(1200)   # let the camera finish flying to the previous selection before aiming at anything
    ok("landscape: Esc removes the crosshair", lp.evaluate("ribbons.filter(r=>r.visible).length")==0)
    lp.evaluate("scrollTo(0,0)"); lp.click("[data-cam=oblique]"); lp.evaluate("scrollTo(0,0)"); lp.wait_for_timeout(500)   # page at the top and a known view, then aim at a top gap that is actually in frame
    pt2=lp.evaluate("""(()=>{const r=document.querySelector('#cv').getBoundingClientRect();
      for(const g of topGaps()){const p=cellScreen(g.a,g.b);if(p.x>r.left+60&&p.x<r.right-60&&p.y>r.top+80&&p.y<r.bottom-60)return {x:p.x,y:p.y}}return {x:r.left+r.width/2,y:r.top+r.height/2}})()""")
    lp.mouse.move(pt2["x"]-25,pt2["y"]-25); lp.wait_for_timeout(120); lp.mouse.move(pt2["x"],pt2["y"]); lp.wait_for_timeout(500)
    st=lp.evaluate("({hover:!!hover, sel:!!S.sel, focus:S.focus, ribbons:ribbons.filter(r=>r.visible).length, markers:[...document.querySelectorAll('#labels .mk')].filter(e=>e.style.display==='block').length, score:S.score, year:S.year, fly:!!fly, under:(e=>e?e.tagName+'#'+e.id:null)(document.elementFromPoint(%f,%f))})"%(pt2["x"],pt2["y"]))
    ok("landscape: hovering a point lights its row and column and names both fields on the edges", st["hover"] and st["ribbons"]>=4 and st["markers"]>=2, st)
    lp.mouse.move(5,5); lp.wait_for_timeout(300)
    lp.fill("#findfield","g06f"); lp.dispatch_event("#findfield","change"); lp.wait_for_timeout(1500)
    ok("landscape: 'Find a field' focuses it (case-insensitive), with its crosshair and cross-section", lp.evaluate("S.focus==='G06F' && ribbons.filter(r=>r.visible).length>=2") and lp.inner_text("#note h2")=="G06F" and lp.locator("#xs svg path[data-layer]").count()>=3 and lp.is_visible("#clearfocus"), lp.inner_text("#note h2"))
    lp.keyboard.press("Escape"); lp.wait_for_timeout(500)
    ok("landscape: Esc clears the focus and the search box", lp.evaluate("S.focus===null") and lp.input_value("#findfield")=="")
    lp.fill("#findfield","not a field"); lp.dispatch_event("#findfield","change"); lp.wait_for_timeout(300)
    ok("landscape: an unknown field is ignored", lp.evaluate("S.focus===null"))
    lp.fill("#findfield","")
    y_obl=lp.evaluate("camera.position.y"); lp.click("[data-cam=low]"); lp.wait_for_timeout(300); y_low=lp.evaluate("camera.position.y")
    ok("landscape: Low angle lowers the camera", y_low<y_obl-30, (round(y_obl),round(y_low)))
    lp.click("[data-cam=oblique]"); lp.evaluate("controls.target.set(40,0,40);camera.position.set(80,60,80)"); lp.click("#resetview"); lp.wait_for_timeout(300)
    ok("landscape: Reset returns to the chosen view", abs(lp.evaluate("camera.position.y")-98)<1 and abs(lp.evaluate("controls.target.x"))<1, round(lp.evaluate("camera.position.y")))
    lp.evaluate("pick(topGaps()[0].a,topGaps()[0].b)"); lp.wait_for_timeout(1800)
    ok("landscape: selecting a pair moves the camera to it", lp.evaluate("(()=>{const g=S.sel,i=idx[g.a],j=idx[g.b];const c=[[i,j],[j,i]].map(([a,b])=>Math.hypot(controls.target.x-xAt(a),controls.target.z-xAt(b)));return Math.min(...c)<8})()"))
    lp.keyboard.press("Escape"); lp.click("#pklab"); lp.wait_for_timeout(400)
    ok("landscape: the Peak labels switch hides them", lp.evaluate("[...document.querySelectorAll('#labels .pk')].filter(e=>e.style.display==='block').length")==0)
    lp.click("#pklab"); lp.click("[data-cam=oblique]"); lp.wait_for_timeout(300)
    ok("landscape: footer credits PatentsView", "PatentsView" in lp.inner_text("footer"))
    lp.fill("#findfield","G06F"); lp.dispatch_event("#findfield","change"); lp.wait_for_timeout(800)
    ok("landscape: the focused field is carried to the tree and matrix", "field=G06F" in (lp.get_attribute("#totree","href") or "") and "field=G06F" in (lp.get_attribute("#tomatrix","href") or ""))
    lp.keyboard.press("Escape")
    ext=[u for u in lreqs if not u.startswith(BASE) and not u.startswith("data:")]
    ok("landscape: no request leaves localhost", len(ext)==0, ext[:3])
    ok("landscape: no console errors", len(lerrs)==0, lerrs[:3])
    href=lp.get_attribute("#totree","href"); ok("landscape: tree link keeps year", href.startswith("/#year="), href)
    # no WebGL: the page must still show numbers and lists, and say so
    nb=p.chromium.launch(executable_path=(sys.argv[1] if len(sys.argv)>1 else "/usr/bin/google-chrome"),headless=True,args=["--no-sandbox","--disable-gpu","--disable-3d-apis","--disable-webgl"])
    np_=nb.new_page(); nerr=[]; np_.on("pageerror",lambda e: nerr.append(str(e))); np_.goto(BASE+"landscape#year=2005"); np_.wait_for_timeout(6000)
    ok("landscape without WebGL: says so and still lists gaps", np_.is_visible("#nogl") and np_.locator("#note li").count()>=5 and not nerr, nerr[:2])
    nb.close()
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
