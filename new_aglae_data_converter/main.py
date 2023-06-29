import argparse
import logging
import pathlib


from enums import ExtractionType

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""Create HDF5 file from AGLAE global files.
        If -e or -d is provided, the CLI mode will be used, otherwise it will launch the GUI app"""
    )
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

    if args.extraction_types and args.data_path:
        from converter import convert

        logger.debug(f"Args: {args}")
        processed_files_cnt = convert(
            extraction_types=tuple(ExtractionType[ext_type.upper()] for ext_type in args.extraction_types),
            data_path=args.data_path,
            output_path=args.output_path,
            lst_config_path=args.config,
        )
        logger.debug("Processed %s files.", processed_files_cnt)
    else:
        from gui import ConverterGUI

        logger.debug("GUI mode")
        ConverterGUI.start()
