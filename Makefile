install:
	curl -sSL https://install.python-poetry.org | python3 -
	poetry env use python3.9
	poetry lock
	poetry install
	
	@echo "Run this to activate your Poetry environment:"
	@echo "source $$(poetry env list --full-path | grep -m1 -o '/.*' | sed 's/ (Activated)//')/bin/activate"

activate:
	@echo "Run this to activate your Poetry environment:"
	@echo "source $$(poetry env list --full-path | grep -m1 -o '/.*' | sed 's/ (Activated)//')/bin/activate"
delete:
	poetry env remove python
run:
	poetry run python app.py

requirements:
	poetry export -f requirements.txt --output requirements.txt --without-hashes
