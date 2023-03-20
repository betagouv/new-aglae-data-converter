class Detector:
    adc: int
    channels: int

class LstConfig:
    x: int
    y: int
    detectors: dict[str, Detector]
