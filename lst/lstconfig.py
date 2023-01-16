from dataclasses import dataclass
from typing import Any


@dataclass
class LstParserConfigOutlets:
    x: int
    y: int
    detectors: dict[int, str]

    def ret_num_adc(self, channel: int) -> str:
        """
        Find the apropriate detector for the given channel
        """
        return self.detectors.get(channel)


def parse(config: dict[str, Any]) -> LstParserConfigOutlets:
    if "x" not in config:
        raise ValueError("Missing x in config")
    if "y" not in config:
        raise ValueError("Missing y in config")
    if "LE0" not in config:
        raise ValueError("Missing LE0 in config")
    if "HE1" not in config:
        raise ValueError("Missing HE1 in config")
    if "HE2" not in config:
        raise ValueError("Missing HE2 in config")
    if "HE3" not in config:
        raise ValueError("Missing HE3 in config")
    if "HE4" not in config:
        raise ValueError("Missing HE4 in config")
    if "HE10" not in config:
        raise ValueError("Missing HE10 in config")
    if "HE11" not in config:
        raise ValueError("Missing HE11 in config")
    if "HE12" not in config:
        raise ValueError("Missing HE12 in config")
    if "HE13" not in config:
        raise ValueError("Missing HE13 in config")
    if "RBS" not in config:
        raise ValueError("Missing RBS in config")
    if "GAMMA" not in config:
        raise ValueError("Missing GAMMA in config")

    detectors: dict[int, str] = {
        config["LE0"]: "LE0",
        config["HE1"]: "HE1",
        config["HE2"]: "HE2",
        config["HE3"]: "HE3",
        config["HE4"]: "HE4",
        config["HE10"]: "HE10",
        config["HE11"]: "HE11",
        config["HE12"]: "HE12",
        config["HE13"]: "HE13",
        config["RBS"]: "RBS",
        config["GAMMA"]: "GAMMA",
    }

    return LstParserConfigOutlets(
        config["x"],
        config["y"],
        detectors,
    )


def default():
    """
    Default configuration for LST parsing
    """
    detectors: dict[int, str] = {
        0b0000000000010000: "LE0",
        0b0000000000000001: "HE1",
        0b0000000000000010: "HE2",
        0b0000000000000100: "HE3",
        0b0000000000001000: "HE4",
        0b0000000000001111: "HE10",
        0b0000000000000011: "HE11",
        0b0000000000001100: "HE12",
        0b0000000000000111: "HE13",
        0b0000000010000000: "RBS",
        0b0000000000100000: "GAMMA",
    }
    return LstParserConfigOutlets(8, 9, detectors=detectors)
