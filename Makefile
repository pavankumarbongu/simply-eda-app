install:
	pip install --upgrade pip
	pip install poetry==1.7.1
	poetry lock
	poetry install
run:
	poetry run python app.py

