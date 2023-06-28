import logging
import pathlib
from typing import Tuple
import h5py
from PyMca5.PyMcaIO import EDFStack
import os

import yaml

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

    processed_files_num = 0
    paths = [data_path] if data_path.is_file() else get_lst_files(data_path)
    for lst_file in paths:
        logger.info("Reading from: %s" % lst_file)

        result = lstrs.parse_lst(str(lst_file.absolute()), config)

        edf_stacks = []
        if config.edf is not None:
            edf_stacks = find_edf_stack(config.edf, data_path)

        write_lst_hdf5(result, edf_stacks, lst_file, output_path)
        processed_files_num += 1

    logger.debug("%s files processed.", processed_files_num)
    return processed_files_num


def find_edf_stack(edf_configs: list[lstrs.EDFConfig], data_path: pathlib.Path) -> list[Tuple[str, EDFStack.EDFStack]]:
    """
    For a given list of EDFConfig and a LST, will try to find associated EDF files.

    :param edf_configs: List of EDFConfig
    :param data_path: Path to the source LST file
    :returns: Tuple of the dataset name (given by the config) and the EDFStack
    """
    stacks: list[Tuple[str, EDFStack.EDFStack]] = []

    for edf_config in edf_configs:
        all_edf_files_list = os.listdir(edf_config.path)
        logger.debug(f"EDF projects: {all_edf_files_list}")

        filename = data_path.name.replace(".lst", "")
        if filename in all_edf_files_list:
            current_path = edf_config.path + "/" + filename
            logger.debug(f"Found current path {current_path}")
            edf_lists = os.listdir(current_path)

            for file_config in edf_config.files:
                filtered_edf_lists = filter(lambda x: file_config.keyword in x, edf_lists)

                logger.debug(f"EDF files: {edf_lists}")
                first_edf_path = None
                for file in filtered_edf_lists:
                    if file.endswith("0000.edf"):
                        first_edf_path = file

                if first_edf_path is not None:
                    edf_stack = EDFStack.EDFStack()
                    edf_stack.loadIndexedStack(current_path + "/" + first_edf_path)
                    stacks.append((file_config.dataset_name, edf_stack))
                    logger.debug(edf_stack.info)
                else:
                    logger.info(f"No EDF found for keyword {file_config.keyword}")

    return stacks


def parse_config(config_file: pathlib.Path) -> lstrs.LstConfig:
    """
    Parse the config file. yaml format.
    """
    with open(config_file, "r") as f:
        logger.debug(f"Opening config file: {config_file}")
        config = yaml.safe_load(f)
        logger.debug("Keys in config file: %s", config.keys())

    detectors: dict[str, lstrs.Detector] = {}
    computed_detectors: dict[str, list[str]] = {}

    for key in config["detectors"]:
        value = config["detectors"][key]

        if isinstance(value, dict):
            adc = value["adc"]
            channels = value["channels"]
            detectors[key] = lstrs.Detector(adc, channels)
        elif isinstance(value, list):
            computed_detectors[key] = value

    edf: list[lstrs.EDFConfig] | None = []
    if "edf" in config:
        logger.debug(config["edf"])
        edf_configs_list = config["edf"]
        for edf_config_dict in edf_configs_list:
            edf_config = lstrs.EDFConfig(edf_config_dict["path"])

            for file in edf_config_dict["files"]:
                edf_file_config = lstrs.EDFFileConfig(keyword=file["keyword"], dataset_name=file["dataset_name"])
                edf_config.files = edf_config.files + [edf_file_config]

            edf.append(edf_config)

    return lstrs.LstConfig(
        config["x"],
        config["y"],
        detectors=detectors,
        computed_detectors=computed_detectors,
        edf=edf,
    )


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


def write_dataset_to_group(group: h5py.Group, dataset: lstrs.LSTData) -> h5py.Dataset:
    logger.debug(f"{dataset.name}: {dataset.data.shape}")

    dset = group.create_dataset(
        dataset.name, shape=dataset.data.shape, dtype="i", data=dataset.data, compression="gzip"
    )

    for key, value in dataset.attributes.items():
        dset.attrs[key] = value

    return dset


def write_lst_hdf5(
    parsing_result: lstrs.ParsingResult,
    edf_stacks: list[Tuple[str, EDFStack.EDFStack]],
    data_path: pathlib.Path,
    output_path: pathlib.Path,
):
    output_file = output_path.joinpath(data_path.name).with_suffix(".hdf5")
    file = h5py.File(output_file, "w")
    data_group = file.create_group("data")

    logger.debug(f"from {data_path} to {output_file}")

    for key, value in parsing_result.attributes.items():
        data_group.attrs[key] = value

    for dataset in parsing_result.datasets:
        write_dataset_to_group(data_group, dataset)

    for computed_dataset in parsing_result.computed_datasets:
        write_dataset_to_group(data_group, computed_dataset)

    for name, edf_stack in edf_stacks:
        data_group.create_dataset(name, data=edf_stack.data, compression="gzip")
