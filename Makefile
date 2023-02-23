init:
	poetry install

run:
	poetry run python gui.py

format:
	poetry run black .

style:
	poetry run black . --check

build_cli:
	poetry run nuitka3 --onefile --standalone --verbose --remove-output --clang converter.py

build_gui:
	poetry run nuitka3 --onefile --standalone --disable-console --verbose --remove-output --plugin-enable=pyside6 --clang gui.py