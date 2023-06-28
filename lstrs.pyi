from numpy import ndarray

class EDFFileConfig:
    keyword: str
    dataset_name: str

class EDFConfig:
    path: str
    files: list[EDFFileConfig]

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

    def __init__(self, adc: int, channels: int) -> None: ...

class LstConfig:
    x: int
    y: int
    detectors: dict[str, Detector]
    edf: EDFConfig | None

    def __init__(
        self,
        x: int,
        y: int,
        detectors: dict[str, Detector],
        computed_detectors: dict[str, list[str]],
        edf: EDFConfig | None,
    ) -> None: ...

def parse_lst(filename: str, config: LstConfig) -> ParsingResult: ...
