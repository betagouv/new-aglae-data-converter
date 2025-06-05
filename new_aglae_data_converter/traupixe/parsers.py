import pathlib
import pandas
import numpy


class TraupixeParser:
    def __init__(self, file: pathlib.Path):
        self.file = file
        self.df = pandas.read_excel(file)

    def get_measuring_points(self):
        return self.df["Unnamed: 0"].dropna().values

    def get_measuring_point_refs(self):
        return self.df["Unnamed: 1"].dropna().values

    def parse_dataset(self):
        detector_name = None
        detector_data: list[tuple[str, pandas.Series]] = []
        for column in self.df.columns:
            # Skip measuring point and reference columns
            if column in ["Unnamed: 0", "Unnamed: 1"]:
                continue

            if not column.startswith("Unnamed:"):
                # Yield the data for the current detector
                if not len(detector_data) == 0:
                    yield detector_name, self._construct_detector_data(detector_data)
                    # Reset the detector data
                    detector_data = []
                # Start a new detector
                detector_name = column
            detector_data.append((self.df[column].values[0], self.df[column].values[1:]))
        yield detector_name, self._construct_detector_data(detector_data)

    def _construct_detector_data(self, data: list[tuple[str, pandas.Series]]):
        # return numpy.array([data[1] for data in data], dtype=[(data[0], numpy.int32) for data in data])
        return numpy.array([data[1] for data in data], dtype=numpy.int32)
