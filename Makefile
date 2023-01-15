init:
	poetry install

run:
	poetry run python gui.py

format:
	poetry run black .