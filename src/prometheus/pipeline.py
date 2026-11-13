"""Aggregate raw PatentsView tables into a small field-level graph (three CSV files).

Input  (tab-separated, as published by PatentsView / USPTO Open Data Portal):
  g_patent             patent_id, patent_date
  g_cpc_current        patent_id, cpc_subclass, [cpc_sequence], [cpc_type]
  g_us_patent_citation patent_id, citation_patent_id
  g_cpc_title          (optional) a column named like cpc_subclass_title

Output (in --out):
  fields.csv        code,title,first_year,n_patents
  builds_on.csv     src,dst,count,first_year        (src "builds on" dst)
  combined_with.csv a,b,count,first_year            (a < b, undirected)
  meta.json         thresholds used, slice used, last grant year, counts

`count` is a total through the end of the data. It is for display only: predictors and
capsules use existence and first_year, because a total would leak the future.

Design notes
  * Column names are detected from the file headers. If one differs from what is
    expected, the error lists the columns found, so it is a one-line fix.
  * Everything is read as text: patent ids such as "D345393" or "RE12345" would
    otherwise be mangled into floats.
  * A patent's "primary" field is its lowest cpc_sequence among inventive codes.
    Citations are attributed to primary fields (a deliberate simplification).
    Combinations use every inventive subclass of a patent.
  * Edge first_year is never earlier than the first_year of either endpoint.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

from . import config
from .slice import SliceRule


class PipelineError(RuntimeError):
    """Raised when an input file does not look as expected."""


def _lit(path: str | Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def _reader(path: str | Path) -> str:
    return (
        f"read_csv({_lit(path)}, delim='\\t', header=true, all_varchar=true, "
        "quote='\"', escape='\"', null_padding=true, ignore_errors=true)"
    )


def _columns(con: duckdb.DuckDBPyConnection, path: str | Path) -> list[str]:
    if not Path(path).exists():
        raise PipelineError(f"File not found: {path}")
    cur = con.execute(f"SELECT * FROM {_reader(path)} LIMIT 0")
    return [d[0] for d in cur.description]


def _pick(cols: list[str], candidates: list[str], what: str, path, required=True):
    lower = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    if required:
        raise PipelineError(
            f"{path}: expected a column for '{what}' named one of {candidates}, "
            f"but the file has: {cols}"
        )
    return None


def aggregate(
    patent_tsv,
    cpc_tsv,
    cites_tsv,
    out_dir,
    titles_tsv=None,
    min_year: int = config.DEFAULT_MIN_YEAR,
    memory_limit: str = "8GB",
    temp_dir: str | None = None,
    keep_work: bool = False,
    log=print,
    slice_rule: SliceRule | None = None,
    min_field_patents: int = config.MIN_FIELD_PATENTS_PER_YEAR,
    min_pair_patents: int = config.MIN_PAIR_PATENTS,
    min_builds_citations: int = config.MIN_BUILDS_CITATIONS,
) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    work = out / "work.duckdb"
    if work.exists():
        work.unlink()
    con = duckdb.connect(str(work))
    con.execute(f"PRAGMA memory_limit='{memory_limit}'")
    if temp_dir:
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
        con.execute(f"PRAGMA temp_directory={_lit(temp_dir)}")

    # ---- patents -------------------------------------------------------
    pc = _columns(con, patent_tsv)
    p_id = _pick(pc, ["patent_id"], "patent id", patent_tsv)
    p_date = _pick(pc, ["patent_date", "grant_date"], "grant date", patent_tsv)
    log(f"[1/6] patents: {patent_tsv}")
    con.execute(
        f"""
        CREATE TABLE pat AS
        SELECT patent_id, year FROM (
          SELECT "{p_id}" AS patent_id,
                 TRY_CAST(substr("{p_date}", 1, 4) AS INTEGER) AS year
          FROM {_reader(patent_tsv)}
        ) WHERE year IS NOT NULL AND year >= {int(min_year)}
        """
    )
    n_pat = con.execute("SELECT count(*) FROM pat").fetchone()[0]
    log(f"      {n_pat:,} patents granted since {min_year}")
    if n_pat == 0:
        raise PipelineError("No patents after applying the year filter; check the date column.")
    data_end_year = con.execute("SELECT max(year) FROM pat").fetchone()[0]

    # ---- classifications ----------------------------------------------
    cc = _columns(con, cpc_tsv)
    c_id = _pick(cc, ["patent_id"], "patent id", cpc_tsv)
    c_sub = _pick(cc, ["cpc_subclass"], "CPC subclass", cpc_tsv)
    c_seq = _pick(cc, ["cpc_sequence", "sequence"], "CPC sequence", cpc_tsv, required=False)
    c_typ = _pick(cc, ["cpc_type", "cpc_category", "category"], "CPC type", cpc_tsv, required=False)
    if c_seq is None:
        log("      WARNING: no cpc_sequence column; primary field per patent is arbitrary.")
    if c_typ is None:
        log("      WARNING: no cpc_type column; using all CPC codes, not only inventive ones.")
    seq_expr = f'TRY_CAST("{c_seq}" AS INTEGER)' if c_seq else "0"
    typ_filter = f"AND lower(\"{c_typ}\") LIKE 'inv%'" if c_typ else ""
    slice_filter = f"AND {slice_rule.sql(chr(34) + c_sub + chr(34))}" if slice_rule else ""
    if slice_rule:
        log(f"      slice '{slice_rule.name}': keeping subclasses with prefixes {slice_rule.include_prefixes}"
            f" (excluding {list(slice_rule.exclude)}); patents without a slice class drop out here")
    log(f"[2/6] classifications: {cpc_tsv}")
    con.execute(
        f"""
        CREATE TABLE cpc_inv AS
        SELECT c.patent_id, c.subclass, min(c.seq) AS seq FROM (
          SELECT "{c_id}" AS patent_id, "{c_sub}" AS subclass, {seq_expr} AS seq
          FROM {_reader(cpc_tsv)}
          WHERE "{c_sub}" IS NOT NULL AND "{c_sub}" <> '' {typ_filter} {slice_filter}
        ) c
        JOIN pat p USING (patent_id)
        GROUP BY c.patent_id, c.subclass
        """
    )
    con.execute(
        """
        CREATE TABLE prim AS
        SELECT patent_id, arg_min(subclass, coalesce(seq, 1000000)) AS subclass
        FROM cpc_inv GROUP BY patent_id
        """
    )
    n_cpc = con.execute("SELECT count(*) FROM cpc_inv").fetchone()[0]
    log(f"      {n_cpc:,} (patent, subclass) rows")

    # ---- fields --------------------------------------------------------
    log("[3/6] fields")
    con.execute(
        f"""
        CREATE TABLE fields AS
        SELECT code, first_year, n_patents FROM (
          SELECT subclass AS code,
                 min(year) FILTER (WHERE n >= {int(min_field_patents)}) AS first_year,
                 sum(n) AS n_patents
          FROM (
            SELECT i.subclass, p.year, count(DISTINCT i.patent_id) AS n
            FROM cpc_inv i JOIN pat p USING (patent_id) GROUP BY 1, 2
          ) GROUP BY 1
        ) WHERE first_year IS NOT NULL
        """
    )
    n_fields = con.execute("SELECT count(*) FROM fields").fetchone()[0]
    log(f"      {n_fields:,} fields")

    title_sql = "CAST(NULL AS VARCHAR)"
    if titles_tsv:
        tc = _columns(con, titles_tsv)
        t_sub = _pick(tc, ["cpc_subclass"], "CPC subclass", titles_tsv)
        t_title = _pick(tc, ["cpc_subclass_title", "subclass_title"], "subclass title", titles_tsv, required=False)
        if t_title:
            con.execute(
                f"""CREATE TABLE titles AS SELECT "{t_sub}" AS code, any_value("{t_title}") AS title
                    FROM {_reader(titles_tsv)} GROUP BY 1"""
            )
            title_sql = "(SELECT t.title FROM titles t WHERE t.code = f.code)"
        else:
            log(f"      WARNING: {titles_tsv} has no subclass-title column ({tc}); titles left blank.")

    # ---- combinations --------------------------------------------------
    log("[4/6] combinations (patents carrying two subclasses) - the heavy step")
    con.execute(
        """
        CREATE TABLE pair_year AS
        SELECT a.subclass AS a, b.subclass AS b, p.year AS year, count(*) AS n
        FROM cpc_inv a
        JOIN cpc_inv b ON a.patent_id = b.patent_id AND a.subclass < b.subclass
        JOIN pat p ON p.patent_id = a.patent_id
        WHERE a.subclass IN (SELECT code FROM fields) AND b.subclass IN (SELECT code FROM fields)
        GROUP BY 1, 2, 3
        """
    )
    con.execute(
        f"""
        CREATE TABLE combined AS
        SELECT x.a, x.b, x.total AS count,
               greatest(x.first_year, fa.first_year, fb.first_year) AS first_year
        FROM (
          SELECT a, b, max(total) AS total,
                 min(year) FILTER (WHERE cum >= {int(min_pair_patents)}) AS first_year
          FROM (
            SELECT a, b, year,
                   sum(n) OVER (PARTITION BY a, b ORDER BY year) AS cum,
                   sum(n) OVER (PARTITION BY a, b) AS total
            FROM pair_year
          ) GROUP BY a, b
        ) x
        JOIN fields fa ON fa.code = x.a JOIN fields fb ON fb.code = x.b
        WHERE x.first_year IS NOT NULL
        """
    )
    n_comb = con.execute("SELECT count(*) FROM combined").fetchone()[0]
    log(f"      {n_comb:,} combined pairs")
    # Extra tables for the stalled-pair overlay and the patent-count size proxy. Both are as-of-able: a first year, and per-year counts
    # (cumulative sums through a cutoff), never an end-of-data total.
    con.execute(
        """
        CREATE TABLE co_assigned AS
        SELECT x.a, x.b, greatest(x.first_year, fa.first_year, fb.first_year) AS first_year
        FROM (SELECT a, b, min(year) AS first_year FROM pair_year GROUP BY a, b) x
        JOIN fields fa ON fa.code = x.a JOIN fields fb ON fb.code = x.b
        """
    )
    con.execute(
        """
        CREATE TABLE field_year AS
        SELECT i.subclass AS code, p.year AS year, count(DISTINCT i.patent_id) AS n
        FROM cpc_inv i JOIN pat p USING (patent_id)
        WHERE i.subclass IN (SELECT code FROM fields) GROUP BY 1, 2
        """
    )

    # ---- citations -----------------------------------------------------
    kc = _columns(con, cites_tsv)
    k_id = _pick(kc, ["patent_id"], "citing patent id", cites_tsv)
    k_cited = _pick(kc, ["citation_patent_id", "cited_patent_id"], "cited patent id", cites_tsv)
    log(f"[5/6] citations: {cites_tsv}  (largest file; takes a while)")
    con.execute(
        f"""
        CREATE TABLE cite_year AS
        SELECT s.subclass AS src, d.subclass AS dst, p.year AS year, count(*) AS n
        FROM (SELECT "{k_id}" AS pid, "{k_cited}" AS cited FROM {_reader(cites_tsv)}) c
        JOIN prim s ON s.patent_id = c.pid
        JOIN prim d ON d.patent_id = c.cited
        JOIN pat p ON p.patent_id = c.pid
        WHERE s.subclass <> d.subclass
          AND s.subclass IN (SELECT code FROM fields) AND d.subclass IN (SELECT code FROM fields)
        GROUP BY 1, 2, 3
        """
    )
    con.execute(
        f"""
        CREATE TABLE builds AS
        SELECT x.src, x.dst, x.total AS count,
               greatest(x.first_year, fs.first_year, fd.first_year) AS first_year
        FROM (
          SELECT src, dst, max(total) AS total,
                 min(year) FILTER (WHERE cum >= {int(min_builds_citations)}) AS first_year
          FROM (
            SELECT src, dst, year,
                   sum(n) OVER (PARTITION BY src, dst ORDER BY year) AS cum,
                   sum(n) OVER (PARTITION BY src, dst) AS total
            FROM cite_year
          ) GROUP BY src, dst
        ) x
        JOIN fields fs ON fs.code = x.src JOIN fields fd ON fd.code = x.dst
        WHERE x.first_year IS NOT NULL
        """
    )
    n_builds = con.execute("SELECT count(*) FROM builds").fetchone()[0]
    log(f"      {n_builds:,} 'builds on' links")

    # ---- write CSVs ----------------------------------------------------
    log("[6/6] writing CSVs")
    con.execute(
        f"""COPY (SELECT f.code, coalesce({title_sql}, '') AS title, f.first_year, f.n_patents
                   FROM fields f ORDER BY f.code)
            TO {_lit(out / 'fields.csv')} (HEADER, DELIMITER ',')"""
    )
    con.execute(
        f"COPY (SELECT src, dst, count, first_year FROM builds ORDER BY src, dst) "
        f"TO {_lit(out / 'builds_on.csv')} (HEADER, DELIMITER ',')"
    )
    con.execute(
        f"COPY (SELECT a, b, count, first_year FROM combined ORDER BY a, b) "
        f"TO {_lit(out / 'combined_with.csv')} (HEADER, DELIMITER ',')"
    )
    con.execute(
        f"COPY (SELECT a, b, first_year FROM co_assigned ORDER BY a, b) "
        f"TO {_lit(out / 'co_assigned.csv')} (HEADER, DELIMITER ',')"
    )
    con.execute(
        f"COPY (SELECT code, year, n FROM field_year ORDER BY code, year) "
        f"TO {_lit(out / 'field_year.csv')} (HEADER, DELIMITER ',')"
    )
    con.close()
    if not keep_work:
        work.unlink(missing_ok=True)
    stats = {"patents": n_pat, "fields": n_fields, "combined_pairs": n_comb, "builds_links": n_builds}
    meta = {
        "source": "patentsview",
        "data_end_year": int(data_end_year),
        "min_year": int(min_year),
        "min_field_patents_per_year": int(min_field_patents),
        "min_pair_patents": int(min_pair_patents),
        "min_builds_citations": int(min_builds_citations),
        "slice": slice_rule.name if slice_rule else "all",
        "slice_prefixes": slice_rule.include_prefixes if slice_rule else [],
        "slice_exclude": list(slice_rule.exclude) if slice_rule else [],
        **stats,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    log(f"done: {stats}")
    return stats
