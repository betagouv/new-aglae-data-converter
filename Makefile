init:
	poetry install

run:
	poetry run python gui.py

format:
	poetry run black .

style:
	poetry run black . --check

build_cli:
	poetry run nuitka3 --onefile --clang converter.py

build_gui:
	poetry run nuitka3 --onefile --plugin-enable=pyside6 --clang gui.py