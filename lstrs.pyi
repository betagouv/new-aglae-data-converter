from numpy import ndarray

class LSTData:
    name: str
    attributes: dict[str, str]
    data: ndarray

class ParsingResult:
    datasets: list[LSTData]
    computed_datasets: list[LSTData]
    attributes: dict[str, str]

class Detector:
    adc: int
    channels: int
    file_extension: str | None

    def __init__(self, adc: int, channels: int, file_extension: str | None) -> None: ...

class ComputedDetector:
    detectors: list[str]
    file_extension: str | None

    def __init__(self, detectors: list[str], file_extension: str | None) -> None: ...

class Config:
    x: int
    y: int
    detectors: dict[str, Detector]
    computed_detectors: dict[str, ComputedDetector]

    def __init__(
        self, x: int, y: int, detectors: dict[str, Detector], computed_detectors: dict[str, list[str]]
    ) -> None: ...

def parse_lst(filename: str, config: Config) -> ParsingResult: ...
