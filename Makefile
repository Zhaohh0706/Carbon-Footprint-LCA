PY := python

.PHONY: sources data notebook test

sources:    ## download the AR5 annex and the OWID dataset; checks the annex SHA-256
	$(PY) scripts/fetch_sources.py

data:       ## derived intensity table
	$(PY) scripts/lca_calculation.py

notebook:   ## rerun the analysis and regenerate every figure
	cd notebooks && $(PY) -m jupyter nbconvert --to notebook --execute --inplace analysis.ipynb

test:
	$(PY) -m pytest -q
