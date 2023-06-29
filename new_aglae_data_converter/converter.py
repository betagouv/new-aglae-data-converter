import logging
import pathlib

from enums import ExtractionType
from globals.converter import convert_globals_to_hdf5
from lst.converter import convert_lst_to_hdf5

logger = logging.getLogger(__name__)


def convert(
    extraction_types: tuple[ExtractionType, ...],
    data_path: pathlib.Path,
    output_path: pathlib.Path,
    lst_config_path: pathlib.Path | None = None,
):
    """
    Extract data files included in `extraction_types` from `data_path` and
    convert them to HDF5 files saved to `output_path`.
    :param extraction_types: Types of extraction to perform.
    :param data_path: Path to the folder containing the data files.
    :param output_path: Path to the folder where the HDF5 files should be saved.
    :param lst_config_path: Path to a config file for lst parsing.
    :return: Number of processed files.
    """
    logger.info("Reading from : %s", data_path)
    logger.info("Saving files to : %s", output_path)

    processed_files_num = 0
    if ExtractionType.GLOBALS in extraction_types or ExtractionType.STANDARDS in extraction_types:
        processed_files_num += convert_globals_to_hdf5(extraction_types, data_path, output_path)
    if ExtractionType.LST in extraction_types:
        processed_files_num += convert_lst_to_hdf5(data_path, output_path, lst_config_path)

    return processed_files_num
