.PHONY: setup test demo real clean-demo

setup:
	pip install -e ".[dev]"

test:
	python3 -m pytest -q

# Everything on SYNTHETIC toy data: no download, a few seconds.
demo:
	techtree toy data/toy
	techtree build data/toy data/toy.rl
	techtree genome data/toy.rl
	techtree backtest data/toy.rl --out results/toy
	techtree capsule data/toy --as-of 1995 --out capsules/toy/1995.rl --seed 0
	techtree capsule data/toy --as-of 2005 --out capsules/toy/2005.rl --seed 0
	techtree baseline-forecast capsules/toy/1995.rl --out results/toy/forecast.json --top 10
	techtree grade results/toy/forecast.json --against capsules/toy/2005.rl --as-of 1995
	@echo "Open results/toy/backtest.md. All of this is synthetic data."

# Real data: set RAW to the folder holding the PatentsView tables (see docs/DATA.md).
RAW ?= data/raw
real:
	techtree pipeline --patent $(RAW)/g_patent.tsv --cpc $(RAW)/g_cpc_current.tsv \
	    --cites $(RAW)/g_us_patent_citation.tsv --out data/csv --slice deeptech
	techtree build data/csv data/techtree.rl
	techtree genome data/techtree.rl
	techtree backtest data/techtree.rl --out results

clean-demo:
	rm -rf data/toy data/toy.rl results/toy capsules/toy
