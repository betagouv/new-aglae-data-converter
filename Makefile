init:
	poetry install

run:
	poetry run python gui.py

format:
	poetry run black .

style:
	poetry run black . --check