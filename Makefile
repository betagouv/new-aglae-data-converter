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

nuitka:
	poetry run nuitka3 --standalone --onefile --assume-yes-for-downloads --enable-plugin=pyside6 --include-package=PyMca5 --include-data-files=lst_config.yml=lst_config.yml --clang new_aglae_data_converter/main.py --output-filename=converter --remove-output
