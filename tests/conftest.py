import pytest

from prometheus import build, toy


@pytest.fixture(scope="session")
def toy_csv(tmp_path_factory):
    d = tmp_path_factory.mktemp("toycsv")
    toy.generate(d, seed=7, structure="strong")
    return d


@pytest.fixture(scope="session")
def toy_store(toy_csv, tmp_path_factory):
    out = tmp_path_factory.mktemp("store") / "toy.rl"
    build.build(toy_csv, out)
    return out


@pytest.fixture(scope="session")
def placebo_store(tmp_path_factory):
    d = tmp_path_factory.mktemp("placebo")
    toy.generate(d / "csv", seed=7, structure="none")
    build.build(d / "csv", d / "placebo.rl")
    return d / "placebo.rl"
