# New AGLAE Data Converter

This project is a tool to convert data files from the New AGLAE particle accelerator to HDF5 format. The tool supports the conversion of imagery analysis data in LST format and spectrum/standards data for punctual analysis. The tool consists of a command-line interface (CLI) and a graphical user interface (GUI) written with Qt.

## Prerequisites

- Python 3.10 or higher
- The following Python packages:
  - h5py
  - numpy
  - pyside6

## Installation

1. Clone the repository to your local machine:
   ```
   git clone https://github.com/your-username/new-aglae-data-converter.git
   ```
2. cd new-aglae-data-converter

   ```
   cd new-aglae-data-converter
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

### GUI

To use the GUI, run the following command:

```
python gui.py
```

Follow the prompts in the GUI to select the source and destination folders and start the conversion process.

### CLI

To use the CLI, run the following command:

```
python converter.py /path/to/source/folder /path/to/destination/folder
```

Replace /path/to/source/folder and /path/to/destination/folder with the actual paths to the source and destination folders on your machine.

## Packaging

To package the project for sharing, you can use the tool [nuitka](https://nuitka.net/). For example, to package the GUI, you can run the following command:

```
nuitka --onefile --plugin-enable=pyside6 --plugin-enable=numpy --clang ./main.py
```

On Windows this will create a single excutable file that you can share with others.

## License

This project is licensed under the [GNU AFFERO GENERAL PUBLIC LICENSE](LICENSE).

## Acknowledgments

- [h5py](https://www.h5py.org/)
- [NumPy](https://numpy.org/)
- [Qt for Python](https://wiki.qt.io/Qt_for_Python)
