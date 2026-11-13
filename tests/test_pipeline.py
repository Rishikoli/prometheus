"""The pipeline on a tiny hand-made PatentsView-style dataset whose answer is known."""
import csv

import pytest

from prometheus import pipeline, slice as slicemod

# id, grant year, [(sequence, subclass, type)]
PATENTS = [
    ("D345393", 1990, [(0, "AAAA", "inventive")]),
    ("RE12345", 1990, [(0, "AAAA", "inventive")]),
    ("5000003", 1991, [(0, "AAAA", "inventive")]),
    ("5000004", 1991, [(0, "AAAA", "inventive")]),
    ("5000011", 1991, [(0, "BBBB", "inventive")]),
    ("5000012", 1991, [(0, "BBBB", "inventive")]),
    ("5000013", 1992, [(0, "BBBB", "inventive")]),
    ("5000014", 1992, [(0, "BBBB", "inventive")]),
    ("5000021", 1993, [(0, "CCCC", "inventive")]),
    ("5000022", 1993, [(0, "CCCC", "inventive")]),
    ("5000031", 1992, [(0, "AAAA", "inventive"), (1, "BBBB", "inventive")]),   # combination 1
    ("5000032", 1993, [(0, "AAAA", "inventive"), (1, "BBBB", "inventive")]),   # combination 2
    ("5000033", 1994, [(0, "AAAA", "inventive"), (1, "CCCC", "inventive")]),   # only one AAAA+CCCC
    ("5000034", 1992, [(0, "AAAA", "inventive"), (1, "CCCC", "additional")]),  # additional: must be ignored
    ("5000041", 1990, [(0, "ZZZZ", "inventive")]),                              # outside the slice
    ("5000042", 1990, [(0, "ZZZZ", "inventive")]),
    ("5000051", 1994, [(0, "YYYY", "inventive")]),                              # tagging section
    ("5000052", 1994, [(0, "YYYY", "inventive")]),
    ("5000061", 1994, [(0, "DDDD", "inventive")]),                              # a single patent: never a field
]
CITES = [("5000011", "D345393"), ("5000012", "RE12345")]  # BBBB patents cite AAAA patents (1991)


def _tsv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(header)
        w.writerows(rows)


@pytest.fixture()
def raw(tmp_path):
    # extra columns on purpose: the reader must pick columns by name
    _tsv(tmp_path / "g_patent.tsv", ["patent_id", "patent_type", "patent_date", "patent_title"],
         [(pid, "utility", f"{y}-06-15", "A patent title") for pid, y, _ in PATENTS])
    _tsv(tmp_path / "g_cpc_current.tsv", ["patent_id", "cpc_sequence", "cpc_section", "cpc_subclass", "cpc_type"],
         [(pid, s, sub[0], sub, t) for pid, _, cl in PATENTS for s, sub, t in cl])
    _tsv(tmp_path / "g_us_patent_citation.tsv", ["patent_id", "citation_sequence", "citation_patent_id"],
         [(a, i, b) for i, (a, b) in enumerate(CITES)])
    return tmp_path


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


KW = dict(min_field_patents=2, min_pair_patents=2, min_builds_citations=2, log=lambda *_: None)


def run(raw, out, **extra):
    return pipeline.aggregate(raw / "g_patent.tsv", raw / "g_cpc_current.tsv", raw / "g_us_patent_citation.tsv",
                              out, **{**KW, **extra})


def test_fields_and_first_years(raw, tmp_path):
    run(raw, tmp_path / "out")
    fields = {r["code"]: r for r in read(tmp_path / "out" / "fields.csv")}
    assert set(fields) == {"AAAA", "BBBB", "CCCC", "ZZZZ", "YYYY"}  # DDDD has a single patent: never a field
    assert fields["AAAA"]["first_year"] == "1990"
    assert fields["BBBB"]["first_year"] == "1991"
    assert fields["CCCC"]["first_year"] == "1993"
    # AAAA appears in 8 patents; the 'additional' CCCC row on 5000034 is not counted for CCCC
    assert fields["AAAA"]["n_patents"] == "8"
    assert fields["CCCC"]["n_patents"] == "3"


def test_combination_needs_enough_patents_and_waits_for_both_fields(raw, tmp_path):
    run(raw, tmp_path / "out")
    comb = read(tmp_path / "out" / "combined_with.csv")
    assert [(r["a"], r["b"], r["first_year"], r["count"]) for r in comb] == [("AAAA", "BBBB", "1993", "2")]
    # AAAA+CCCC has one inventive patent only (the other is 'additional'), so no edge


def test_threshold_is_a_parameter(raw, tmp_path):
    run(raw, tmp_path / "out", min_pair_patents=3)
    assert read(tmp_path / "out" / "combined_with.csv") == []


def test_builds_on_from_citations_to_primary_fields(raw, tmp_path):
    run(raw, tmp_path / "out")
    b = read(tmp_path / "out" / "builds_on.csv")
    assert [(r["src"], r["dst"], r["count"], r["first_year"]) for r in b] == [("BBBB", "AAAA", "2", "1991")]


def test_slice_drops_other_and_tagging_classes(raw, tmp_path):
    rule = slicemod.from_dict({"name": "t", "include": {"x": ["AAA", "BBB", "CCC", "DDD", "YYY"]}, "exclude": ["Y"]})
    run(raw, tmp_path / "out", slice_rule=rule)
    fields = {r["code"] for r in read(tmp_path / "out" / "fields.csv")}
    assert fields == {"AAAA", "BBBB", "CCCC"}
    meta = __import__("json").loads((tmp_path / "out" / "meta.json").read_text())
    assert meta["slice"] == "t" and meta["data_end_year"] == 1994 and meta["min_pair_patents"] == 2


def test_missing_column_lists_what_was_found(raw, tmp_path):
    _tsv(raw / "g_cpc_current.tsv", ["patent_id", "cpc_group"], [("x", "A01B1/00")])
    with pytest.raises(pipeline.PipelineError) as e:
        run(raw, tmp_path / "out")
    assert "cpc_subclass" in str(e.value) and "cpc_group" in str(e.value)


def test_slice_rule_rejects_bad_prefixes():
    with pytest.raises(slicemod.SliceError):
        slicemod.from_dict({"include": {"x": ["a'; DROP"]}})
    with pytest.raises(slicemod.SliceError):
        slicemod.from_dict({"include": {}})


def test_bundled_slice_loads_and_matches():
    rule = slicemod.load("deeptech")
    assert rule.matches("G06N") and rule.matches("H10D") and not rule.matches("A01B") and not rule.matches("Y02E")
    assert slicemod.load("all") is None
