from dataclasses import dataclass, field
from typing import Any

from lstrs import LstConfig


@dataclass
class LstParserConfigOutlets:
    x: int
    y: int
    detectors: dict[int, str]
    computed_detectors: dict[str, list[str]] = field(default_factory=dict)
    max_channels_for_detectors: dict[str, int] = field(default_factory=dict)


def parse(config: dict[str, Any]) -> LstParserConfigOutlets:

    detectors_mapping = config["detectors"]

    detectors: dict[int, str] = {}
    computed_detectors: dict[str, list[str]] = {}
    max_channels_for_detectors: dict[str, int] = {}

    for key in detectors_mapping:
        value = detectors_mapping[key]

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
