import json

from prometheus.cli import main


def test_end_to_end_on_toy_data(tmp_path, capsys):
    csv, store, results = tmp_path / "csv", tmp_path / "toy.rl", tmp_path / "results"
    assert main(["toy", str(csv), "--seed", "7"]) == 0
    assert main(["build", str(csv), str(store)]) == 0
    assert main(["info", str(store)]) == 0
    assert main(["gaps", str(store), "--as-of", "2000", "--top", "3"]) == 0
    assert main(["knockout", str(store), "TOY001", "--top", "3"]) == 0
    assert main(["ancestors", str(store), "TOY100"]) == 0
    assert main(["evidence", str(store), "TOY050", "TOY090", "--as-of", "2005"]) == 0
    assert main(["backtest", str(store), "--out", str(results)]) == 0
    assert (results / "backtest.md").exists() and json.loads((results / "backtest.json").read_text())["gate"]
    assert main(["genome", str(store)]) == 0
    assert main(["relatives", str(store), "TOY040", "--k", "3"]) == 0
    assert main(["capsule", str(csv), "--as-of", "1995", "--out", str(tmp_path / "caps" / "1995.rl")]) == 0
    assert main(["capsule", str(csv), "--as-of", "2005", "--out", str(tmp_path / "caps" / "2005.rl")]) == 0
    fc = tmp_path / "forecast.json"
    assert main(["baseline-forecast", str(tmp_path / "caps" / "1995.rl"), "--out", str(fc), "--top", "10"]) == 0
    capsys.readouterr()
    assert main(["grade", str(fc), "--against", str(tmp_path / "caps" / "2005.rl"), "--as-of", "1995"]) == 0
    graded = json.loads(capsys.readouterr().out)
    assert graded["pairs_valid"] == 10 and graded["with_cypher"] == 10
    assert main(["order", str(store), "--as-of", "2000"]) == 0
    order = json.loads(capsys.readouterr().out)
    assert len(order["order"]) > 50


def test_errors_are_one_line_not_tracebacks(tmp_path, capsys):
    assert main(["build", str(tmp_path / "nope"), str(tmp_path / "x.rl")]) == 2
    assert "error:" in capsys.readouterr().err
