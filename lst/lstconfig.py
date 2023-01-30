from dataclasses import dataclass
from typing import Any


@dataclass
class LstParserConfigOutlets:
    x: int
    y: int
    detectors: dict[int, str]
    computed_detectors: dict[str, list[str]] = None
    max_channels_for_detectors: dict[str, int] = None


def parse(config: dict[str, Any]) -> LstParserConfigOutlets:

    detectors_keys = config["detectors"]

    detectors: dict[int, str] = {}
    computed_detectors: dict[str, list[str]] = {}
    max_channels_for_detectors: dict[str, int] = {}

    for key in detectors_keys:
        value = detectors_keys[key]

        if isinstance(value, dict):
            detectors[value["adc"]] = key
            max_channels_for_detectors[key] = value["channels"]
        elif isinstance(value, list):
            computed_detectors[key] = value

    return LstParserConfigOutlets(
        config["x"],
        config["y"],
        detectors,
        computed_detectors,
        max_channels_for_detectors,
    )
