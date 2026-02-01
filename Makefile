PYTHON := python

.PHONY: install install-dev uninstall clean format format-check lint typecheck test test-verbose coverage default

default: format lint typecheck test coverage

# Installation targets
install:
	$(PYTHON) -m pip install .

install-dev:
	$(PYTHON) -m pip install -e ".[dev]"

uninstall:
	$(PYTHON) -m pip uninstall -y ap-copy-master-to-blink

clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

format: install-dev
	$(PYTHON) -m black ap_copy_master_to_blink tests

format-check: install-dev
	$(PYTHON) -m black --check ap_copy_master_to_blink tests

lint: install-dev
	$(PYTHON) -m flake8 --max-line-length=88 --extend-ignore=E203,W503,E501,F401 ap_copy_master_to_blink tests

typecheck: install-dev
	$(PYTHON) -m mypy ap_copy_master_to_blink || true

# Testing (install deps first, then run tests)
test: install-dev
	$(PYTHON) -m pytest

test-verbose: install-dev
	$(PYTHON) -m pytest -v

coverage: install-dev
	$(PYTHON) -m pytest --cov=ap_copy_master_to_blink --cov-report=term
