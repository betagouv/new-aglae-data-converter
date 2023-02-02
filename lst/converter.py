import logging
import pathlib

import h5py
import yaml

import lst.lstconfig as LstConfig
from lst.parser import LstParser

logger = logging.getLogger(__name__)


def convert_lst_to_hdf5(
    data_path: pathlib.Path,
    output_path: pathlib.Path,
    config_path: pathlib.Path = None,
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

    processed_files_num = 0
    for lst_file in get_lst_files(data_path):
        logger.info("Reading from: %s" % lst_file)

        parser = LstParser(filename=lst_file, config=config)

        file_h5 = h5py.File(output_path / f"{lst_file.stem}.hdf5", mode="w")

        map_info, exp_info = parser.parse_header()
        logger.debug(f"map_info: {map_info}")
        logger.debug(f"exp_info: {exp_info}")

        parser.parse_dataset(map_info, file_h5)
        parser.add_metadata_to_hdf5(file_h5, map_info, exp_info)
        file_h5.close()
        processed_files_num += 1
    logger.debug("%s files processed.", processed_files_num)
    return processed_files_num


def parse_config(config_file: pathlib.Path) -> LstConfig.LstParserConfigOutlets:
    """
    Parse the config file. yaml format.
    """
    with open(config_file, "r") as f:
        logger.debug(f"Opening config file: {config_file}")
        config = yaml.safe_load(f)

    try:
        config = LstConfig.parse(config)
    except TypeError as e:
        logger.error(f"Error parsing config file: {e}")
        raise e

    return config


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
