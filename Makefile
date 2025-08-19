activate:
	@echo "Run this to activate your Poetry environment:"
	@echo "source $$(poetry env list --full-path | grep -m1 -o '/.*' | sed 's/ (Activated)//')/bin/activate"
install:
	curl -k -sSL https://install.python-poetry.org | python3 -
	poetry self add poetry-plugin-export
	poetry lock
	poetry install
	poetry env use python3
	
run:
	poetry run python app.py

requirements:
	poetry export -f requirements.txt --output requirements.txt --without-hashes
