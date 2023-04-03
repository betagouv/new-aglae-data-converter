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
