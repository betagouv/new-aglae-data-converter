import pathlib
import os
import logging
from typing import Tuple

from PyMca5.PyMcaIO import EDFStack
import lstrs

logger = logging.getLogger(__name__)


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
        logger.debug(f"all EDF projects: {all_edf_files_list}")

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
        else:
            logger.debug(f"No EDF found for file {filename}")

    return stacks
