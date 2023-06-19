import logging
import pathlib
import h5py

import yaml

import lstrs

from lstrs import ParsingResult

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
        write_lst_hdf5(result, lst_file, output_path)
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
    computed_detectors: dict[str, list[str]] = {}

    for key in config["detectors"]:
        value = config["detectors"][key]

        if isinstance(value, dict):
            adc = value["adc"]
            channels = value["channels"]
            detectors[key] = lstrs.Detector(adc, channels)
        elif isinstance(value, list):
            computed_detectors[key] = value

    return lstrs.LstConfig(
        config["x"],
        config["y"],
        detectors=detectors,
        computed_detectors=computed_detectors,
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


def write_dataset_to_group(group: h5py.Group, dataset: lstrs.LSTData):
    logger.debug(f"{dataset.name}: {dataset.data.shape}")

    dset = group.create_dataset(
        dataset.name, shape=dataset.data.shape, dtype="i", data=dataset.data, compression="gzip"
    )

    for key, value in dataset.attributes.items():
        dset.attrs[key] = value


def write_lst_hdf5(parsing_result: ParsingResult, data_path: pathlib.Path, output_path: pathlib.Path):
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
