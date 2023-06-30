from numpy import ndarray

class EDFFileConfig:
    keyword: str
    dataset_name: str

    def __init__(self, keyword: str, dataset_name: str) -> None: ...

class EDFConfig:
    path: str
    files: list[EDFFileConfig]

    def __init__(self, path: str) -> None: ...

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

    def __init__(self, adc: int, channels: int) -> None: ...

class LstConfig:
    x: int
    y: int
    detectors: dict[str, Detector]
    computed_detectors: dict[str, ComputedDetector]
    edf: list[EDFConfig] | None

    def __init__(
        self,
        x: int,
        y: int,
        detectors: dict[str, Detector],
        computed_detectors: dict[str, list[str]],
        edf: list[EDFConfig] | None,
    ) -> None: ...

def parse_lst(filename: str, config: Config) -> ParsingResult: ...
