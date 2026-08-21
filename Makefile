.PHONY: install demo lint format test coverage api report manifest verify ci clean-generated

install:
	python -m pip install -e ".[dev]"

demo:
	python scripts/run_demo.py

lint:
	ruff check .

format:
	ruff format .

test:
	pytest

coverage:
	pytest --cov=aurelia_sme_sales --cov-report=term-missing --cov-branch

api:
	uvicorn aurelia_sme_sales.api:app --reload

report:
	python scripts/build_executive_report.py

manifest:
	python scripts/build_manifest.py

verify:
	python scripts/verify_artifacts.py

ci: lint coverage

clean-generated:
	python scripts/clean_generated.py
