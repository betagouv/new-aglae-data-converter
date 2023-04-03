import io
from abc import ABC, abstractmethod

import numpy


class HeaderReadingError(Exception):
    pass


class BaseParser(ABC):
    def __init__(self, file: io.TextIOWrapper):
        self.file = file

    @abstractmethod
    def parse_header(self) -> tuple[tuple[str, str], ...]:
        pass

    @abstractmethod
    def seek_dataset(self):
        """Change file object position at the beginning of the dataset, i.e
        after the header."""
        pass

    @abstractmethod
    def parse_dataset(self):
        pass


class SpectrumParser(BaseParser):

    dataset_dt = numpy.dtype(int)

    def parse_header(self) -> list[tuple[str, str]]:
        if self.file.tell():
            self.file.seek(0)

        self.file.readline()
        try:
            header_line = self.file.readline().rstrip()
            (
                year,
                month,
                seconds,
                acquisition_time,
                spectrum_sum,
                *additional_data,
            ) = header_line.split(" ")
        except ValueError as error:
            raise HeaderReadingError(f"Could not parse header of file {self.file.name}") from error
        # BUG prone if user comment may contain comma
        user_comment, *experiment_info = " ".join(additional_data).split(",")

        return [
            ("year", year),
            ("month", month),
            ("seconds since midnight", seconds),
            ("acquisition time", acquisition_time),
            ("spectrum sum", spectrum_sum),
            ("user comment", user_comment),
            ("experiment information", ",".join(experiment_info)),
        ]

    def parse_dataset(self):
        self.seek_dataset()
        return numpy.fromfile(self.file, dtype=int, sep="\n")

    def seek_dataset(self):
        self.file.seek(0)
        self.file.readline()
        self.file.readline()


class RBSParser(BaseParser):

    # dataset_dt = numpy.dtype([("", int, (2,))])
    x_range: int | None = None

    def parse_header(self) -> tuple[tuple[str, str], ...]:
        if self.file.tell():
            self.file.seek(0)

        header = []
        self.file.readline()  # [DISPLAY]

        while True:
            line = self.file.readline().split("=")
            if line == ["\n"]:  # end of header
                break
            if len(line) == 1:  # no value
                key = line[0]
                value = ""
            else:
                key, value = line
            if key == "NAME":
                user_comment, *experiment_info = " ".join(value).split(",")
                header.append(("user comment", user_comment.rstrip()))
                header.append(("experiment information", ",".join(experiment_info).rstrip()))
            if key == "XRANGE":
                self.x_range = int(value)
            header.append((key, value.rstrip()))
        if not header:
            raise HeaderReadingError(f"Could not parse header of file {self.file.name}")
        return header

    def parse_dataset(self):
        self.seek_dataset()
        return numpy.loadtxt(self.file, dtype=int, delimiter="\t", max_rows=self.x_range)

    def seek_dataset(self):
        self.file.seek(0)
        while self.file.readline() != "[DATA]\n":
            continue
        self.file.readline()
