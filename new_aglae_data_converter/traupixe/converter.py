"""Convert Excel file from Traupixe to HDF5 format."""

from __future__ import annotations

import logging
import os
import pathlib

import h5py
import numpy
import lstrs
from .parsers import TraupixeParser

logger = logging.getLogger(__name__)


def convert_traupixe_to_hdf5(
    data_path: pathlib.Path,
    output_path: pathlib.Path,
    config: lstrs.Config,
) -> int:
    """
    Convert traupixe xlsx files to HDF5 format and save them to the specified output path.
    :param data_path: Path to the folder containing the traupixe files.
    :param output_path: Path to the folder where the HDF5 files should be saved.
    :return: Number of processed files.
    """
    # Open output HDF5 file
    output_file = h5py.File(output_path / "traupixe.hdf5", mode="w")

    # Get global data files in the specified folder
    data_files = get_data_files(data_path, config)

    if output_file is None:
        logger.error("No HDF5 file opened for file %s.", file.name)

    logger.info("Starting reading files...")
    num_processed_files = 0
    for file in data_files:
        # Insert the data from the global file into the appropriate HDF5 file
        insert_traupixe_file_in_hdf5(output_file, file)
        num_processed_files += 1

    logger.info("%s files processed.", num_processed_files)
    return num_processed_files


def insert_traupixe_file_in_hdf5(hdf5_group: h5py.Group | h5py.File, data_file: pathlib.Path):
    """
    Insert the data from a traupixe file into an HDF5 group/file.
    :param hdf5_group: HDF5 group/file to insert the data into.
    :param data_file: Traupixe file to extract the data from.
    """
    file_description = data_file.name.split(".")[0].replace("TRAUPIXE-", "")

    # Create a group for the measure point in the HDF5 file
    measure_point_group = hdf5_group.require_group(file_description)

    # Return if the file is empty
    if os.stat(data_file).st_size == 0:
        return

    parser = TraupixeParser(data_file)

    ds = parser.parse_dataset()

    detectors_data = []

    for detector, data in ds:
        measure_point_group.create_dataset(detector, data=data, compression="gzip")
        detectors_data.append(data[:21])

    detectors_np_data = numpy.array(detectors_data)
    measure_point_group.create_dataset("all", data=detectors_np_data, compression="gzip")


def get_data_files(folder: pathlib.Path, config: lstrs.Config) -> list[pathlib.Path]:
    files = folder.glob("**/*")
    global_files: list[pathlib.Path] = list(filter(lambda file: file.name.startswith("TRAUPIXE-"), files))
    return sorted(global_files)
