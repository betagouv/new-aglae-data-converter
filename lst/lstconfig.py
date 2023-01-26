from dataclasses import dataclass
from typing import Any


@dataclass
class LstParserConfigOutlets:
    x: int
    y: int
    detectors: dict[int, str]
    computed_detectors: dict[str, list[str]] = None


def parse(config: dict[str, Any]) -> LstParserConfigOutlets:

    detectors_keys = config["detectors"]

    detectors: dict[int, str] = {}
    computed_detectors: dict[str, list[str]] = {}

    for key in detectors_keys:
        value = detectors_keys[key]

        if isinstance(value, int):
            detectors[value] = key
        elif isinstance(value, list):
            computed_detectors[key] = value

    return LstParserConfigOutlets(
        config["x"],
        config["y"],
        detectors,
        computed_detectors,
    )


def default():
    """
    Default configuration for LST parsing
    """
    detectors: dict[int, str] = {
        16: "LE0",
        1: "HE1",
        2: "HE2",
        4: "HE3",
        8: "HE4",
        32: "RBS",
        64: "GAMMA",
    }

    computed_detectors: dict[str, list[str]] = {
        "HE10": ["HE1", "HE2", "HE3", "HE4"],
        "HE11": ["HE1", "HE2"],
        "HE12": ["HE3", "HE4"],
        "HE13": ["HE1", "HE2", "HE3"],
    }

    return LstParserConfigOutlets(
        256, 512, detectors=detectors, computed_detectors=computed_detectors
    )
