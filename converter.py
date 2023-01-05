import argparse
import logging
import os
import pathlib

import h5py

from parsers import RBSParser, SpectrumParser

logger = logging.getLogger(__name__)

# List of valid file extensions for global data files
GLOBALS_FILE_EXTENSIONS = [
    "g7",
    "g27",
    "r8",
    "r9",
    "x0",
    "x1",
    "x2",
    "x3",
    "x4",
    "x10",
    "x11",
    "x12",
    "x13",
]


def convert_globals_to_hdf5(data_path: pathlib.Path, output_path: pathlib.Path):
    """
    Convert global data files to HDF5 format and save them to the specified output path.
    :param data_path: Path to the folder containing the global data files.
    :param output_path: Path to the folder where the HDF5 files should be saved.
    :return: Number of processed files.
    """
    logger.info("Reading from : %s" % data_path)
    logger.info("Saving files to : %s" % output_path)

    # Open HDF5 files for globals and standards data
    globals_file = h5py.File(output_path / "globals.hdf5", mode="w")
    standards_file = h5py.File(output_path / "std.hdf5", mode="w")

    # Get global data files in the specified folder
    data_files = get_global_files(data_path)
    logger.info("Starting reading files...")
    num_processed_files = 0
    for global_file in data_files:
        # Determine whether the current file contains standards or globals data
        file = standards_file if "_std_" in global_file.name else globals_file
        # Insert the data from the global file into the appropriate HDF5 file
        insert_global_file_in_hdf5(file, global_file)
        num_processed_files += 1
    logger.info("%s files processed." % num_processed_files)
    logger.info("Done.")
    return num_processed_files


def insert_global_file_in_hdf5(hdf5_group: h5py.Group, global_file: pathlib.Path):
    """
    Insert the data from a global file into an HDF5 group/file.
    :param hdf5_group: HDF5 group/file to insert the data into.
    :param global_file: Global file to extract the data from.
    """
    # Extract start date, measure point, and reference object from the file name
    start_date, measure_point, ref_object = global_file.name.split("_")[:3]
    # Extract the detector name from the file extension
    detector = global_file.suffix[1:]
    # Create a group for the measure point in the HDF5 file
    measure_point_group = hdf5_group.require_group(measure_point)
    # Add attributes to the measure point group
    measure_point_group.attrs.create("start date", start_date)
    measure_point_group.attrs.create("ref object", ref_object)
    # Return if the file is empty
    if os.stat(global_file).st_size == 0:
        return
    # Populate the detector dataset with the data from the global file
    populate_detector_dataset(measure_point_group, detector, global_file)


def populate_detector_dataset(
    parent_group: h5py.Group, detector_name: str, global_file: pathlib.Path
):
    """
    Populate an HDF5 dataset with the data from a global file.
    :param parent_group: HDF5 group containing the dataset.
    :param detector_name: Name of the detector.
    :param global_file: Global file to extract the data from.
    """
    with open(global_file, "r") as file:
        # Extract attributes from header
        if global_file.suffix in [".r8", ".r9"]:
            parser = RBSParser(file)
        else:
            parser = SpectrumParser(file)

        header = parser.parse_header()

        # Create dataset and populate data
        detector_dataset = parent_group.create_dataset(
            detector_name, data=parser.parse_dataset()
        )
        # Add attributes to dataset
        for key, value in header:
            detector_dataset.attrs.create(key, value)


def get_global_files(folder: pathlib.Path):
    """
    Get all global data files in the specified folder.
    :param folder: Folder to search for global data files.
    :return: Iterator of global data files.
    """
    files = folder.glob("**/*")
    for file in files:
        if file.suffix[1:] in GLOBALS_FILE_EXTENSIONS:
            yield file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create HDF5 file from AGLAE global files."
    )
    parser.add_argument(
        "data_path",
        metavar="Data path",
        type=pathlib.Path,
        help="The path to the the globals data folder.",
    )
    parser.add_argument(
        "output_path",
        metavar="Output path",
        type=pathlib.Path,
        help="The path to the the globals data folder.",
    )

    args = parser.parse_args()
    convert_globals_to_hdf5(args.data_path, args.output_path)
