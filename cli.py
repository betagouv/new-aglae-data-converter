import argparse
import pathlib
import logging
import h5py
import yaml
from lst.parser import LstParser
import lst.lstconfig as LstConfig

logger = logging.getLogger(__name__)


def convert_lst_to_hdf5(
    data_path: pathlib.Path,
    output_path: pathlib.Path,
    config: LstConfig.LstParserConfigOutlets,
):
    """
    Convert lst files to HDF5 format and save them to the specified output path.
    """
    logger.info("Reading from: %s" % data_path)
    logger.info("Saving files to: %s" % output_path)

    # Open HDF5 for the lst data file
    # h5_file = h5py.File(output_path / f"{data_path.name}.hdf5", mode="w")

    parser = LstParser(filename=data_path, config=config)
    logger.info("Starting reading files...")

    file_h5 = h5py.File(output_path / f"{data_path.name}.hdf5", mode="w")

    map_info, exp_info = parser.parse_header()
    logger.debug(f"map_info: {map_info}")
    logger.debug(f"exp_info: {exp_info}")

    parser.parse_dataset(map_info, file_h5)
    logger.info("Done.")


def parse_config(config_file: pathlib.PosixPath) -> LstConfig.LstParserConfigOutlets:
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create HDF5 file from AGLAE global files."
    )
    parser.add_argument(
        "data_path",
        metavar="Data path",
        type=pathlib.PosixPath,
        help="The path to the the lst data file",
    )

    parser.add_argument(
        "output_path",
        metavar="Output path",
        type=pathlib.Path,
        help="The path to the the globals data folder.",
    )

    parser.add_argument(
        "--config", "-c", type=pathlib.PosixPath, help="Path to config file"
    )

    parser.add_argument("--log", default="INFO", help="Log level (default: INFO)")

    args = parser.parse_args()

    # Setup logger
    numeric_level = getattr(logging, args.log.upper(), None)
    logging.basicConfig(level=numeric_level)

    # Parse config file
    if args.config:
        config = parse_config(args.config)
    else:
        config = LstConfig.default()

    logger.debug(f"Config: {config}")

    convert_lst_to_hdf5(args.data_path, args.output_path, config)
