class Detector:
    adc: int
    channels: int

    def __init__(self, adc: int, channels: int) -> None: ...

class LstConfig:
    x: int
    y: int
    detectors: dict[str, Detector]

    def __init__(
        self, x: int, y: int, detectors: dict[str, Detector], computed_detectors: dict[str, list[str]]
    ) -> None: ...

def parse_lst(filename: str, output_path: str, config: LstConfig) -> None: ...
