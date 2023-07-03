from __future__ import annotations

import logging
import os
import pathlib

import h5py
import lstrs
from enums import ExtractionType
from globals.parsers import BaseParser, RBSParser, SpectrumParser


logger = logging.getLogger(__name__)


def convert_globals_to_hdf5(
    extraction_types: tuple[ExtractionType, ...],
    data_path: pathlib.Path,
    output_path: pathlib.Path,
    config: lstrs.Config,
) -> int:
    """
    Convert global data files to HDF5 format and save them to the specified output path.
    :param data_path: Path to the folder containing the global data files.
    :param output_path: Path to the folder where the HDF5 files should be saved.
    :return: Number of processed files.
    """
    # Open HDF5 files for globals and standards data
    globals_file: h5py.File | None = None
    standards_file: h5py.File | None = None
    if ExtractionType.GLOBALS in extraction_types:
        globals_file = h5py.File(output_path / "globals.hdf5", mode="a")
    if ExtractionType.STANDARDS in extraction_types:
        standards_file = h5py.File(output_path / "std.hdf5", mode="a")

    # Get global data files in the specified folder
    data_files = get_global_files(data_path, config)
    logger.info("Starting reading files...")
    num_processed_files = 0
    for global_file in data_files:
        # Determine whether the current file contains standards or globals data
        if is_file_std(global_file.name):
            if not standards_file:
                continue
            file = standards_file
        else:
            if not globals_file:
                continue
            file = globals_file

        file = standards_file if is_file_std(global_file.name) else globals_file

        # Insert the data from the global file into the appropriate HDF5 file
        if file is not None:
            insert_global_file_in_hdf5(file, global_file)
            num_processed_files += 1
        else:
            logger.error("No HDF5 file opened for file %s.", global_file.name)

    logger.info("%s files processed.", num_processed_files)
    return num_processed_files


def insert_global_file_in_hdf5(hdf5_group: h5py.Group | h5py.File, global_file: pathlib.Path):
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
    measure_point_group.attrs.create("start_date", start_date)
    measure_point_group.attrs.create("object_ref", ref_object)
    # Return if the file is empty
    if os.stat(global_file).st_size == 0:
        return

    with open(global_file, "r", encoding="utf-8") as file:
        # Extract attributes from header
        if global_file.suffix in [".r8", ".r9", ".r150", ".r135"]:
            parser = RBSParser(file)
        else:
            parser = SpectrumParser(file)

        populate_measure_point_group_attributes(measure_point_group, parser)

        # Populate the detector dataset with the data from the global file
        if detector not in measure_point_group:
            measure_point_group.create_dataset(detector, data=parser.parse_dataset(), compression="gzip")


def populate_measure_point_group_attributes(measure_point_group: h5py.Group, parser: BaseParser):
    header = parser.parse_header()
    if not header:
        return
    experiment_information = header.pop("experiment_information")
    flatten_header = {**header, **experiment_information}

    measure_point_attrs_keys = measure_point_group.attrs.keys()
    # if the group is empty or not fully populated, populate parent attributes with fist detector header
    # only for spectrum files because rbs files do not have all attributes
    if not measure_point_attrs_keys or len(measure_point_attrs_keys) < len(flatten_header.keys()):
        for key, value in flatten_header.items():
            measure_point_group.attrs.create(key, value)


def get_global_files(folder: pathlib.Path, config: lstrs.Config) -> list[pathlib.Path]:
    """
    Get all global data files in the specified folder.
    :param folder: Folder to search for global data files.
    :return: Iterator of global data files.
    """
    files = folder.glob("**/*")
    global_extensions = _get_global_file_extensions(config)
    global_files: list[pathlib.Path] = list(filter(lambda file: file.suffix[1:] in global_extensions, files))
    return sorted(global_files)


def is_file_std(filename: str) -> bool:
    return "_std_" in filename.lower()


def _get_global_file_extensions(config: lstrs.Config) -> set[str]:
    detector_extensions = [detector.file_extension or name for name, detector in config.detectors.items()]
    computed_detector_extensions = [
        detector.file_extension or name for name, detector in config.computed_detectors.items()
    ]
    return set(detector_extensions + computed_detector_extensions)
