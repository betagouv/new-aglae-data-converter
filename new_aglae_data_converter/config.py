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

    edf: list[lstrs.EDFConfig] = []
    if "edf" in config:
        edf_configs_list = config["edf"]
        for edf_config_dict in edf_configs_list:
            edf_config = lstrs.EDFConfig(edf_config_dict["path"])

            for file in edf_config_dict["files"]:
                edf_file_config = lstrs.EDFFileConfig(keyword=file["keyword"], dataset_name=file["dataset_name"])
                edf_config.files = edf_config.files + [edf_file_config]

            edf.append(edf_config)

    return lstrs.Config(
        config["x"],
        config["y"],
        detectors=detectors,
        computed_detectors=computed_detectors,
        edf=edf,
    )
