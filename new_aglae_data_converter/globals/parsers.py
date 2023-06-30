import io
from abc import ABC, abstractmethod
from typing import TypedDict

import numpy


class HeaderReadingError(Exception):
    pass


class ExperimentInformation(TypedDict):
    area_of_interest: str
    map_size_width: str
    map_size_height: str
    pixel_size_width: str
    pixel_size_height: str
    pen_size: str
    sample_speed_rate: str
    calibration_factor: str
    particle: str
    beam_energy: str
    le0_filter: str
    he1_filter: str
    he2_filter: str
    he3_filter: str
    he4_filter: str


class Header(TypedDict):
    year: str
    month: str
    seconds_since_midnight: str
    acquisition_time: str
    spectrum_sum: str

    experiment_information: ExperimentInformation


class BaseParser(ABC):
    def __init__(self, file: io.TextIOWrapper):
        self.file = file

    @abstractmethod
    def parse_header(self) -> Header | None:
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

    def parse_header(self):
        if self.file.tell():
            self.file.seek(0)

        self.file.readline()
        try:
            line = self.file.readline()
            header_line = line.rstrip()
            (
                year,
                month,
                seconds,
                acquisition_time,
                spectrum_sum,
                *additional_data,
            ) = header_line.split(" ")
            experiment_information = _parse_spectrum_exp_info(additional_data)
        except ValueError as error:
            raise HeaderReadingError(
                f"Could not parse header of file {self.file.name}.\n\nerror: {error}\nline: {line}"
            ) from error

        return {
            "year": year,
            "month": month,
            "seconds_since_midnight": seconds,
            "acquisition_time": acquisition_time,
            "spectrum_sum": spectrum_sum,
            "experiment_information": experiment_information,
        }

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

    def parse_header(self):
        return None  # because RBS files do not have relevant information in the header

    def parse_dataset(self):
        self.seek_dataset()
        return numpy.loadtxt(self.file, dtype=int, delimiter="\t", max_rows=self.x_range)

    def seek_dataset(self):
        self.file.seek(0)
        while self.file.readline() != "[DATA]\n":
            continue
        self.file.readline()


def _parse_spectrum_exp_info(experiment_info: str) -> ExperimentInformation:
    # BUG prone if user comment may contain comma
    (
        area_of_interest,
        map_size_width,
        map_size_height,
        pixel_size_width,
        pixel_size_height,
        pen_size,
        sample_speed_rate,
        calibration_factor,
        particle,
        beam_energy,
        le0_filter,
        he1_filter,
        he2_filter,
        he3_filter,
        he4_filter,
        *_,
    ) = map(str.strip, " ".join(experiment_info).split(","))
    return {
        "area_of_interest": area_of_interest[1:],
        "map_size_width": map_size_width,
        "map_size_height": map_size_height,
        "pixel_size_width": pixel_size_width,
        "pixel_size_height": pixel_size_height,
        "pen_size": pen_size,
        "sample_speed_rate": sample_speed_rate,
        "calibration_factor": calibration_factor,
        "particle": particle,
        "beam_energy": beam_energy,
        "le0_filter": le0_filter,
        "he1_filter": he1_filter,
        "he2_filter": he2_filter,
        "he3_filter": he3_filter,
        "he4_filter": he4_filter[:-1],
    }
