# Inspired from https://doc.qt.io/qtforpython/examples/example_network__downloader.html

from PySide6.QtWidgets import (
    QWidget,
    QApplication,
    QMessageBox,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QStyle,
    QFileDialog,
    QTextEdit,
)
from PySide6.QtCore import QDir, Slot, QThread, Signal
import sys

from converter import convert_globals_to_hdf5
import pathlib


class ConverterWorker(QThread):

    finished_signal = Signal(int)

    data_path: pathlib.Path | None = None
    output_path: pathlib.Path | None = None

    def __init__(self):
        super().__init__()

    def run(self):
        num_processed_files = convert_globals_to_hdf5(self.data_path, self.output_path)
        self.finished_signal.emit(num_processed_files)


class ConverterWidget(QWidget):
    """A widget to download a http file to a destination file"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.worker = ConverterWorker()
        self.worker.finished_signal.connect(self.on_conversion_completed)

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
        self.context_box.setDisabled(True)
        self.context_box.setText(
            "Select source & destination paths then press start button."
        )

        # buttons bar layout
        hlayout = QHBoxLayout()
        hlayout.addStretch()
        hlayout.addWidget(self.start_button)

        contexlayout = QVBoxLayout()
        contexlayout.addStretch()
        contexlayout.addWidget(self.context_box)

        # main layout
        vlayout = QVBoxLayout(self)
        vlayout.addWidget(self.source_path_box)
        vlayout.addWidget(self.dest_path_box)
        vlayout.addStretch()
        vlayout.addLayout(hlayout)
        vlayout.addLayout(contexlayout)

        self.resize(600, 300)

        self.start_button.clicked.connect(self.on_start)
        self.start_button.setDisabled(True)

    @Slot()
    def on_start(self):
        """When user press start button"""
        dest_path = pathlib.Path(
            QDir.fromNativeSeparators(self.dest_path_box.text().strip())
        )
        source_path = pathlib.Path(
            QDir.fromNativeSeparators(self.source_path_box.text().strip())
        )

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
        self.worker.start()
        self.context_box.append("Conversion has started.")

    @Slot()
    def on_conversion_completed(self, num_processed_files: int):
        self.start_button.setDisabled(False)
        self.context_box.append("Done.")
        self.context_box.append("Processed %s files." % num_processed_files)

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
        dir_path = QFileDialog.getExistingDirectory(
            self, "Open Directory", QDir.homePath(), QFileDialog.ShowDirsOnly
        )
        if dir_path:
            return QDir(dir_path)
        return None

    def _validate_form(self):
        if self.dest_path_box.text() and self.source_path_box.text():
            self.start_button.setDisabled(False)
            self.context_box.append("Ready ?")


if __name__ == "__main__":

    app = QApplication(sys.argv)
    w = ConverterWidget()
    w.show()
    sys.exit(app.exec())
