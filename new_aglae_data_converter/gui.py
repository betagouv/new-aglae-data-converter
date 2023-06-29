import pathlib
import sys

from PySide6.QtCore import QDir, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStyle,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from converter import convert
from enums import ExtractionType


class ConverterWorker(QThread):
    finished_signal = Signal(int)
    failed_signal = Signal(Exception)

    data_path: pathlib.Path | None = None
    output_path: pathlib.Path | None = None
    extraction_types: tuple[ExtractionType, ...] = None
    lst_config_path: pathlib.Path | None = None

    def __init__(self):
        super().__init__()

    def run(self):
        try:
            processed_files_num = convert(
                self.extraction_types,
                self.data_path,
                self.output_path,
                self.lst_config_path,
            )
        except Exception as error:
            self.failed_signal.emit(error)
        self.finished_signal.emit(processed_files_num)


class ConverterWidget(QWidget):
    """A widget to download a http file to a destination file"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("NewAGLAE HDF5 converter")

        self.worker = ConverterWorker()
        self.worker.finished_signal.connect(self.on_conversion_completed)
        self.worker.failed_signal.connect(self.on_conversion_failure)

        self.start_button = QPushButton("Start")
        self.start_button.setDisabled(True)

        self.source_path_box = QLineEdit()
        self.source_path_box.setPlaceholderText("Run data folder path")
        self.source_path_box.addAction(
            qApp.style().standardIcon(QStyle.SP_DirOpenIcon), QLineEdit.TrailingPosition
        ).triggered.connect(self.on_source_path_click)

        self.dest_path_box = QLineEdit()
        self.dest_path_box.setPlaceholderText("Destination folder path")
        self.dest_path_box.addAction(
            qApp.style().standardIcon(QStyle.SP_DirOpenIcon), QLineEdit.TrailingPosition
        ).triggered.connect(self.on_dest_path_click)

        self.context_box = QTextEdit()
        self.context_box.setReadOnly(True)
        self.context_box.setText("Select source & destination paths then press start button.")

        # buttons bar layout
        buttonslayout = QHBoxLayout()
        buttonslayout.addStretch()
        buttonslayout.addWidget(self.start_button)

        self.checkboxeslayout = ExtractionTypeChexboxesLayout()

        # main layout
        vlayout = QVBoxLayout(self)
        vlayout.addWidget(self.source_path_box)
        vlayout.addWidget(self.dest_path_box)
        vlayout.addSpacing(12)
        vlayout.addLayout(self.checkboxeslayout)
        vlayout.addSpacing(12)
        self.config_file_input_layout = ConfigFileInputLayout()
        vlayout.addLayout(self.config_file_input_layout)
        vlayout.addLayout(buttonslayout)
        vlayout.addWidget(self.context_box)

        self.resize(600, 300)

        self.start_button.clicked.connect(self.on_start)
        self.start_button.setDisabled(True)

    @Slot()
    def on_start(self):
        """When user press start button"""
        dest_path = pathlib.Path(QDir.fromNativeSeparators(self.dest_path_box.text().strip()))
        source_path = pathlib.Path(QDir.fromNativeSeparators(self.source_path_box.text().strip()))

        # Ask a question if file already exists
        output_files = (
            dest_path / "globals.hdf5",
            dest_path / "std.hdf5",
        )
        if any(file.exists() for file in output_files):
            ret = QMessageBox.question(
                self,
                "Files exist",
                "Do you want to override the standards and globals files ?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret == QMessageBox.No:
                return

        self.start_button.setDisabled(True)
        self.worker.output_path = dest_path
        self.worker.data_path = source_path
        self.worker.extraction_types = self.checkboxeslayout.selected_extractions
        if self.config_file_input_layout.config_file:
            self.worker.lst_config_path = pathlib.Path(self.config_file_input_layout.config_file)
        self.worker.start()
        self.context_box.append(
            "Selected extraction types : {}.".format(
                ", ".join(etype.name.lower() for etype in self.worker.extraction_types)
            )
        )
        self.context_box.append("Conversion has started.")

    @Slot()
    def on_conversion_completed(self, processed_files_num):
        self.start_button.setDisabled(False)
        self.context_box.append(f"Processed {processed_files_num} files.")
        self.context_box.append("Done.")

    @Slot()
    def on_conversion_failure(self, error: Exception):
        self.start_button.setDisabled(False)
        self.context_box.append(f"An error occured : {error} ({type(error).__name__})")
        raise type(error) from error

    @Slot()
    def on_source_path_click(self):
        directory = self._on_path_box_click()
        if directory:
            self.source_path_box.setText(QDir.fromNativeSeparators(directory.path()))
            self._validate_form()

    @Slot()
    def on_dest_path_click(self):
        directory = self._on_path_box_click()
        if directory:
            self.dest_path_box.setText(QDir.fromNativeSeparators(directory.path()))
            self._validate_form()

    def _on_path_box_click(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Open Directory", QDir.homePath(), QFileDialog.ShowDirsOnly)
        if dir_path:
            return QDir(dir_path)
        return None

    def _validate_form(self):
        if self.dest_path_box.text() and self.source_path_box.text():
            self.start_button.setDisabled(False)
            self.context_box.append("Ready ?")


class ExtractionTypeChexboxesLayout(QHBoxLayout):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.checkboxes: dict[ExtractionType, QCheckBox] = {
            ExtractionType.LST: QCheckBox("LST"),
            ExtractionType.GLOBALS: QCheckBox("Globals"),
            ExtractionType.STANDARDS: QCheckBox("Standards"),
        }

        title = QLabel()
        title.setText("Extraction type")
        self.addWidget(title)

        extract_choice_group = QButtonGroup()
        extract_choice_group.setExclusive(False)
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)
            extract_choice_group.addButton(checkbox)
            self.addWidget(checkbox)

    @property
    def selected_extractions(self) -> tuple[ExtractionType, ...]:
        return tuple(extraction for extraction, checkbox in self.checkboxes.items() if checkbox.isChecked())


class ConfigFileInputLayout(QVBoxLayout):
    def __init__(self):
        super().__init__()
        title = QLabel()
        title.setText("Config file (optional)")
        self.addWidget(title)

        self.config_path_box = QLineEdit()
        self.config_path_box.setPlaceholderText("Run data folder path")
        self.config_path_box.addAction(
            qApp.style().standardIcon(QStyle.SP_DirOpenIcon), QLineEdit.TrailingPosition
        ).triggered.connect(self.on_path_click)
        self.addWidget(self.config_path_box)

    @property
    def config_file(self) -> str | None:
        return self.config_path_box.text() or None

    @Slot()
    def on_path_click(self):
        file_path = QFileDialog.getOpenFileName(
            caption="Open configuration file",
            dir=QDir.homePath(),
            filter="Config Files (*.yaml, *.yml)",
        )
        if file_path:
            self.config_path_box.setText(file_path[0])


class ConverterGUI:
    @staticmethod
    def start():
        app = QApplication(sys.argv)
        w = ConverterWidget()
        w.show()
        sys.exit(app.exec())
