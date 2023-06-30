import logging
import pathlib

import lstrs
import yaml

logger = logging.getLogger(__name__)


def parse_config(config_file: pathlib.Path) -> lstrs.Config:
    """
    Parse the config file. yaml format.
    """
    with open(config_file, "r") as f:
        logger.debug(f"Opening config file: {config_file}")
        config = yaml.safe_load(f)

    detectors: dict[str, lstrs.Detector] = {}
    computed_detectors: dict[str, lstrs.ComputedDetector] = {}

    for key, value in config["detectors"].items():
        detectors[key] = lstrs.Detector(value["adc"], value["channels"], value.get("file_extension"))
    for key, value in config["computed_detectors"].items():
        computed_detectors[key] = lstrs.ComputedDetector(
            value["detectors"],
            value.get("file_extension"),
        )

    return lstrs.Config(
        config["x"],
        config["y"],
        detectors=detectors,
        computed_detectors=computed_detectors,
    )
