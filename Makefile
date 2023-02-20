init:
	poetry install

run:
	poetry run python new_aglae_data_converter/gui.py

format:
	poetry run black .

style:
	poetry run black . --check

build_rs:
	poetry run maturin develop --release

build_cli:
	poetry run nuitka3 --onefile --plugin-enable=numpy --clang ./converter.py

build_gui:
	poetry run nuitka3 --onefile --plugin-enable=numpy --plugin-enable=pyside6 --clang ./gui.py
