.PHONY: setup test demo real clean-demo

setup:
	pip install -e ".[dev]"

test:
	python3 -m pytest -q

# Everything on SYNTHETIC toy data: no download, a few seconds.
demo:
	prometheus toy data/toy
	prometheus build data/toy data/toy.rl
	prometheus genome data/toy.rl
	prometheus backtest data/toy.rl --out results/toy
	prometheus capsule data/toy --as-of 1995 --out capsules/toy/1995.rl --seed 0
	prometheus capsule data/toy --as-of 2005 --out capsules/toy/2005.rl --seed 0
	prometheus baseline-forecast capsules/toy/1995.rl --out results/toy/forecast.json --top 10
	prometheus grade results/toy/forecast.json --against capsules/toy/2005.rl --as-of 1995
	@echo "Open results/toy/backtest.md. All of this is synthetic data."

# Real data: set RAW to the folder holding the PatentsView tables (see docs/DATA.md).
RAW ?= data/raw
real:
	prometheus pipeline --patent $(RAW)/g_patent.tsv --cpc $(RAW)/g_cpc_current.tsv \
	    --cites $(RAW)/g_us_patent_citation.tsv --out data/csv --slice deeptech
	prometheus build data/csv data/prometheus.rl
	prometheus genome data/prometheus.rl
	prometheus backtest data/prometheus.rl --out results

clean-demo:
	rm -rf data/toy data/toy.rl results/toy capsules/toy
