import logging
import pathlib
from typing import Tuple

import h5py
import lstrs
from lstrs import ParsingResult
from PyMca5.PyMcaIO import EDFStack
from new_aglae_data_converter.edf import find_edf_stack

logger = logging.getLogger(__name__)


def convert_lst_to_hdf5(
    data_path: pathlib.Path,
    output_path: pathlib.Path,
    config: lstrs.Config,
) -> int:
    """
    Convert lst files to HDF5 format and save them to the specified output path.
    :return: Number of processed files.
    """
    processed_files_num = 0
    paths = [data_path] if data_path.is_file() else get_lst_files(data_path)
    for lst_file in paths:
        logger.info("Reading from: %s" % lst_file)

        result = lstrs.parse_lst(str(lst_file.absolute()), config)

        edf_stacks = []
        if config.edf is not None:
            edf_stacks = find_edf_stack(config.edf, lst_file)

        write_lst_hdf5(result, edf_stacks, lst_file, output_path)
        processed_files_num += 1

    logger.debug("%s files processed.", processed_files_num)
    return processed_files_num


def get_lst_files(folder: pathlib.Path):
    """
    Get all lst data files in the specified folder.
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


def write_lst_hdf5(
    parsing_result: ParsingResult,
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
