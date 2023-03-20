import logging
import pathlib

import yaml

import lst.lstconfig as LstConfig
import lstrs

logger = logging.getLogger(__name__)


def convert_lst_to_hdf5(
    data_path: pathlib.Path,
    output_path: pathlib.Path,
    config_path: pathlib.Path | None = None,
) -> int:
    """
    Convert lst files to HDF5 format and save them to the specified output path.
    :return: Number of processed files.
    """
    # Throw error if no config file is provided
    if not config_path:
        config_path = pathlib.Path("./lst_config.yml")
    if not config_path.exists():
        raise ValueError("Default config file is missing. Provide a config file.")
    config = parse_config(config_path)
    logger.debug(f"Config: {config}")

    def process_file(lst_file: pathlib.Path):
        logger.info("Reading from: %s" % lst_file)

        lstrs.parse_lst(str(lst_file.absolute()), str(output_path.absolute()), config)

    if data_path.is_file():
        process_file(data_path)
        return 1

    processed_files_num = 0
    for lst_file in get_lst_files(data_path):
        process_file(lst_file)
        processed_files_num += 1

    logger.debug("%s files processed.", processed_files_num)
    return processed_files_num


def parse_config(config_file: pathlib.Path) -> lstrs.LstConfig:
    """
    Parse the config file. yaml format.
    """
    with open(config_file, "r") as f:
        logger.debug(f"Opening config file: {config_file}")
        config = yaml.safe_load(f)

    detectors: dict[str, lstrs.Detector] = {}

    for key in config["detectors"]:
        value = config["detectors"][key]

        if isinstance(value, dict):
            adc = value["adc"]
            channels = value["channels"]
            detectors[key] = lstrs.Detector(adc, channels)

    return lstrs.LstConfig(config["x"], config["y"], detectors=detectors)


def get_lst_files(folder: pathlib.Path):
    """
    Get all global data files in the specified folder.
    :param folder: Folder to search for global data files.
    :return: Iterator of global data files.
    """
    files = folder.glob("**/*")
    for file in files:
        if file.suffix[1:] == "lst":
            yield file
