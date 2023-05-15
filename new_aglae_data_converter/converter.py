import argparse
import logging
import pathlib
import typing

from enums import ExtractionType
from globals.converter import convert_globals_to_hdf5
from lst.converter import convert_lst_to_hdf5

logger = logging.getLogger(__name__)


def convert(
    extraction_types: tuple[ExtractionType, ...],
    data_path: pathlib.Path,
    output_path: pathlib.Path,
    lst_config_path: typing.Optional[pathlib.Path] = None,
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create HDF5 file from AGLAE global files.")
    parser.add_argument(
        "--extraction-types",
        "-e",
        metavar="Extraction types",
        type=str,
        nargs="+",
        choices=("lst", "globals", "standards"),
        help="The data types to extract and convert. "
        "Choices are 'lst', 'globals' and 'standards'. "
        "Example: python converter.py -e lst globals -d ... -o ...",
    )
    parser.add_argument(
        "--data-path",
        "-d",
        metavar="Data path",
        type=pathlib.Path,
        help="Path to the the globals data folder.",
    )
    parser.add_argument(
        "--output-path",
        "-o",
        metavar="Output path",
        type=pathlib.Path,
        help="Path to the the globals data folder.",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=pathlib.Path,
        help="Path to config file for LST parsing.",
        required=False,
    )
    parser.add_argument("--log", default="INFO", help="Log level (default: INFO)")

    args = parser.parse_args()

    # Setup logger
    numeric_level = getattr(logging, args.log.upper(), None)
    logging.basicConfig(level=numeric_level)

    processed_files_cnt = convert(
        extraction_types=tuple(ExtractionType[ext_type.upper()] for ext_type in args.extraction_types),
        data_path=args.data_path,
        output_path=args.output_path,
        lst_config_path=args.config,
    )
    logger.debug(f"Processed %s files.", processed_files_cnt)
