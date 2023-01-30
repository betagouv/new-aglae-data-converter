from functools import lru_cache
from logging import getLogger
from pathlib import PosixPath
from math import ceil
from h5py import File
from datetime import datetime
import numpy as np

from .models import LstParserResponseMap, LstParserResponseExpInfo
from .lstconfig import LstParserConfigOutlets

logger = getLogger(__name__)


@lru_cache
def get_adcnum(binary_value: int) -> list[str]:
    adcnum = []
    # low is telling us what outlets are triggered
    # As low is 16 bits, we check each position if
    # the bits are set to 1
    for bits in range(16):
        value_bin = 0b0000000000000001 << bits
        if binary_value & value_bin:
            adcnum.append(value_bin)

    return adcnum


@lru_cache
def is_event(binary_value: int) -> bool:
    return binary_value >> 16 != 0x8000


class LstParser:
    def __init__(
        self,
        filename: PosixPath,
        config: LstParserConfigOutlets,
    ):
        self.filename = filename
        self.lstconfig = config

    def parse_header(self) -> tuple[LstParserResponseMap, LstParserResponseExpInfo]:
        """
        Parse the header of the lst file

        Returns:
            A tuple containing the map info and exp info
        """

        logger.debug("Parsing header of lst file %s", self.filename)
        if not self.filename.is_file():
            raise ValueError("Path is not a file")
        elif not self.filename.name.endswith(".lst"):
            raise ValueError("File is not a lst file")
        elif not self.filename:
            raise ValueError("Invalid file name")
        elif not self.filename.exists():
            raise ValueError("File does not exist")

        # Open file file in read and binary mode
        file_handler = open(self.filename, "rb")

        # The beginning of the file contains the UTF-8 header
        data_bytes = file_handler.readline()

        map_info: LstParserResponseMap = None
        exp_info: LstParserResponseExpInfo = None

        while data_bytes:
            data_bytes = file_handler.readline()
            decoded_line = data_bytes.decode("utf-8").strip()

            if decoded_line == "[LISTDATA]":
                break
            elif "Map size" in decoded_line:
                map_info = self.__parse_map_size(decoded_line)
            elif "Exp.Info" in decoded_line:
                exp_info = self.__parse_exp_info(decoded_line)

        file_handler.close()
        logger.debug("Finished parsing header of lst file %s", self.filename)

        return map_info, exp_info

    def parse_dataset(self, response_map: LstParserResponseMap, file: File):
        """
        Parse the dataset of the lst file
        """
        max_x = ceil(response_map.map_size_width / response_map.pixel_size_width)
        max_y = ceil(response_map.map_size_height / response_map.pixel_size_height)

        file_handler = open(self.filename, "rb")
        binary_mode = False

        data_byte = file_handler.readline()
        while data_byte:
            if not binary_mode:
                data_byte = file_handler.readline()
                decoded_line = data_byte.decode("utf-8").strip()
                if decoded_line == "[LISTDATA]":
                    binary_mode = True
                    break

        if not binary_mode:
            raise ValueError("Invalid lst file")

        execution_started_at = datetime.now()
        nb_events: dict[str, int] = {}

        for detector in self.lstconfig.detectors:
            nb_events[self.lstconfig.detectors[detector]] = 0

        big_dset = self.__create_datasets_for_detectors(
            max_x, max_y, self.lstconfig.detectors
        )
        # Log dismension of the dataset
        logger.debug("Dataset shape: %s", big_dset.shape)

        while data_byte:
            try:
                data_byte = file_handler.read(4)
            except:
                data_byte = b"\xff\xff\xff\xff"

            # Don't know why
            if data_byte == b"\xff\xff\xff\xff":
                file_handler.read(4)

            binary_value = int.from_bytes(data_byte, byteorder="little", signed=False)

            # binary_value is the shape of 0x[high][low]
            # Check if high is 0x8000
            if is_event(binary_value):
                continue

            pos_x, pos_y, channels, adcnum = -1, -1, {}, get_adcnum(binary_value)

            if len(adcnum) % 2 != 0:
                # If we have an odd number, extra 8 bits will be added
                # to fill the 16 bits
                file_handler.read(2)

            for adc in adcnum:
                val = file_handler.read(2)
                int_value = int.from_bytes(val, byteorder="little", signed=True)

                if adc == self.lstconfig.x and int_value > 0 and int_value < max_x:
                    pos_x = int_value
                elif adc == self.lstconfig.y and int_value > 0 and int_value < max_y:
                    pos_y = int_value
                else:
                    plug = self.__ret_num_adc(adc)
                    if plug is not None:
                        max_value = self.__get_max_channels_for_detectors(plug)
                        if int_value < max_value:
                            channels[plug] = int_value

            if pos_x >= 0 and pos_y >= 0:
                for ch in channels:
                    min_z = self.__get_floor_for_detector(ch)
                    big_dset[pos_x, pos_y, min_z + channels[ch]] += 1
                    nb_events[ch] += 1

        file_handler.close()

        # Display how long it took to parse the file in seconds and/or minutes
        execution_ended_at = datetime.now()
        execution_time = execution_ended_at - execution_started_at
        logger.debug("Parsing took %s", execution_time)

        datasets: dict[str, np.ndarray] = {}

        # Write datasets into the file
        z_index = 0
        for detector_name in nb_events:
            logger.debug("z_index %s", z_index)
            max_z = self.__get_max_channels_for_detectors(detector_name)
            # Slice big_dset into smaller datasets
            if nb_events[detector_name] > 0:
                dset = big_dset[:, :, z_index : z_index + max_z]
                logger.debug("dset shape: %s", dset.shape)
                file.create_dataset(f"/{detector_name}", data=dset)
                logger.debug("Created dataset %s", detector_name)
                datasets[detector_name] = dset

            z_index += max_z

        for computed_detector in self.lstconfig.computed_detectors:
            logger.debug("Creating computed detector %s", computed_detector)
            detectors = self.lstconfig.computed_detectors[computed_detector]

            # Find max channels for all detectors
            max_channels = 0
            for detector in detectors:
                max_channels = max(
                    max_channels, self.__get_max_channels_for_detectors(detector)
                )

            # Create a dataset for the computed detector
            dset = np.zeros((max_x, max_y, max_channels), dtype=np.uint32)

            used_detectors = []
            # Add all detectors to the computed detector
            for detector in detectors:
                if detector in datasets:
                    dset = np.add(dset, datasets[detector])
                    used_detectors.append(detector)

            file.create_dataset(f"/{computed_detector}", data=dset)
            logger.debug("Created dataset %s using %s", computed_detector, used_detectors)

        logger.debug("Found %s events", nb_events)
        logger.debug("total events: %s", sum(nb_events.values()))
        logger.debug("Finished parsing dataset of lst file %s", self.filename)
        return

    @lru_cache
    def __ret_num_adc(self, channel: int) -> str:
        """
        Find the apropriate detector for the given channel
        """
        return self.lstconfig.detectors.get(channel)

    def __create_datasets_for_detectors(
        self, max_x: int, max_y: int, detectors: list[str]
    ) -> np.ndarray:
        max_z = 0
        for detector in detectors:
            max_channels = self.__get_max_channels_for_detectors(detectors[detector])
            logger.debug("Max channels for %s: %s", detectors[detector], max_channels)
            max_z += max_channels

        return np.zeros((max_x, max_y, max_z), dtype="u4")

    @lru_cache
    def __get_floor_for_detector(self, detector: str) -> int:
        """
        Get the floor for the given detector
        """
        min_z = 0
        for detec in self.lstconfig.detectors:
            detector_name = self.lstconfig.detectors[detec]
            if detector_name == detector:
                break
            min_z += self.__get_max_channels_for_detectors(detector_name)

        return min_z

    @lru_cache
    def __get_max_channels_for_detectors(self, detector: str) -> int:
        return self.lstconfig.max_channels_for_detectors.get(detector, 1024)

    def __parse_map_size(self, line: str) -> LstParserResponseMap:
        """
        Parse the map size and pixel size
        """

        # The map size is in the format "map_size_w, map_size_h, pixel_size_w, pixel_size_h, pen_size"
        content_to_parse = line.split(":")[1]
        data = content_to_parse.split(",")

        map_info = LstParserResponseMap()
        map_info.map_size_width = int(data[0])
        map_info.map_size_height = int(data[1])
        map_info.pixel_size_width = int(data[2])
        map_info.pixel_size_height = int(data[3])
        map_info.pen_size = int(data[4])

        return map_info

    def __parse_exp_info(self, line: str) -> LstParserResponseExpInfo:
        """
        Parse the experiment info
        """

        # The experiment info is in the format "date, object, project"
        content_to_parse = line.split(":")[1]
        data = content_to_parse.split(",")

        exp_info = LstParserResponseExpInfo()
        exp_info.particle = data[0]
        exp_info.beam_energy = data[1]
        exp_info.le0_filter = data[2]
        exp_info.he1_filter = data[3]
        exp_info.he2_filter = data[4]
        exp_info.he3_filter = data[5]
        exp_info.he4_filter = data[6]

        return exp_info
