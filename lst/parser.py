import logging
import pathlib
import math
import h5py
from datetime import datetime

from .models import LstParserResponseMap, LstParserResponseExpInfo
from .lstconfig import LstParserConfigOutlets

logger = logging.getLogger(__name__)


def get_max_channels_for_detectors(detector: str) -> int:
    switcher = {
        "LE0": 2048,
        "HE1": 2048,
        "HE2": 2048,
        "HE3": 2048,
        "HE4": 2048,
        "HE10": 2048,
        "HE11": 2048,
        "HE12": 2048,
        "HE13": 2048,
        "RBS": 512,
        "GAMMA": 4096,
    }

    return switcher.get(detector, 1024)


class LstParser:
    def __init__(
        self,
        filename: pathlib.PosixPath,
        config: LstParserConfigOutlets,
    ):
        self.filename = filename
        self.outlets_config = config

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

    def parse_dataset(self, response_map: LstParserResponseMap, file: h5py.File):
        """
        Parse the dataset of the lst file
        """
        max_x = math.ceil(response_map.map_size_width / response_map.pixel_size_width)
        max_y = math.ceil(response_map.map_size_height / response_map.pixel_size_height)

        file_handler = open(self.filename, "rb")
        binary_mode = False
        nb_events = 0

        datasets: dict[str, h5py.Dataset] = {}

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

        lst_content = file_handler.read()
        index = 0

        while index < len(lst_content) - 20:
            try:
                data_byte = lst_content[index : index + 4]
                index += 4
            except:
                data_byte = b"\xff\xff\xff\xff"

            # Don't know why
            if data_byte == b"\xff\xff\xff\xff":
                index += 4

            binary_value = int.from_bytes(data_byte, byteorder="little", signed=False)

            # Keep only the first 16 bits
            high = int(binary_value >> 16)

            # binary_value is the shape of 0x[high][low]
            # high is a keyword
            # low is the value of that interest us

            if high == 0x8000:
                adcnum: list[int] = []

                # low is telling us what outlets are triggered
                # As low is 16 bits, we check each position if
                # the bits are set to 1
                for bits in range(16):
                    value_bin = 0b0000000000000001 << bits
                    if binary_value & value_bin:
                        adcnum.append(value_bin)

                if len(adcnum) % 2 != 0:
                    # If we have an odd number, extra 8 bits will be added
                    # to fill the 16 bits
                    index += 2

                pos_x = -1
                pos_y = -1
                channels: dict[str, int] = {}

                for adc in adcnum:
                    val = lst_content[index : index + 2]
                    int_value = int.from_bytes(val, byteorder="little", signed=True)

                    if (
                        adc == self.outlets_config.x
                        and int_value > 0
                        and int_value < max_x
                    ):
                        pos_x = int_value
                    elif (
                        adc == self.outlets_config.y
                        and int_value > 0
                        and int_value < max_y
                    ):
                        pos_y = int_value
                    else:
                        plug = self.outlets_config.ret_num_adc(adc)
                        if plug is not None:
                            max_value = get_max_channels_for_detectors(plug)
                            if int_value < max_value:
                                channels[plug] = int_value

                    index += 2

                if pos_x >= 0 and pos_y >= 0:
                    for ch in channels:
                        self.__handle_channel(
                            file,
                            datasets,
                            max_x,
                            max_y,
                            ch,
                            channels[ch],
                            pos_x,
                            pos_y,
                        )
                    nb_events += 1

        file_handler.close()

        # Display how long it took to parse the file in seconds and/or minutes
        execution_ended_at = datetime.now()
        execution_time = execution_ended_at - execution_started_at
        logger.debug("Parsing took %s", execution_time)

        logger.debug("Found %s events", nb_events)
        logger.debug("Finished parsing dataset of lst file %s", self.filename)
        return

    def __handle_channel(
        self,
        file: h5py.File,
        datasets: dict[str, h5py.Dataset],
        max_x: int,
        max_y: int,
        detector: str,
        value: int,
        x: int,
        y: int,
    ):
        dset = datasets.get(detector)

        if dset is None:
            max_channels = get_max_channels_for_detectors(detector)
            dset = file.create_dataset(
                f"/{detector}",
                (max_x, max_y, max_channels),
                dtype="u4",
            )
            logger.debug("Created dataset %s", dset)
            datasets[detector] = dset
            dset[x, y, value] = 1
        else:
            dset[x, y, value] += 1

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
