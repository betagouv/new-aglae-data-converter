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
	poetry run nuitka3 --onefile --standalone --verbose --remove-output --clang new_aglae_data_converter/converter.py

build_gui:
	poetry run nuitka3 --onefile --standalone --disable-console --verbose --remove-output --plugin-enable=pyside6 --clang new_aglae_data_converter/gui.py
