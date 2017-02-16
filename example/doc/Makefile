.PHONY: all
all: sphinx

# doctrees used for searching
SPHINXOPTS=-n -W -d _build/doctrees .

.PHONY: sphinx

sphinx:
	PYTHON=$(which python3) sphinx-build -b html $(SPHINXOPTS) _build/html
