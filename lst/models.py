from dataclasses import dataclass, field


@dataclass
class LstParserResponseMap:
    map_size_width: int = field(default=0)
    map_size_height: int = field(default=0)
    pixel_size_width: int = field(default=0)
    pixel_size_height: int = field(default=0)
    pen_size: int = field(default=0)


@dataclass
class LstParserResponseExpInfo:
    particle: str = field(default="")
    beam_energy: str = field(default="")
    le0_filter: str = field(default="")
    he1_filter: str = field(default="")
    he2_filter: str = field(default="")
    he3_filter: str = field(default="")
    he4_filter: str = field(default="")


@dataclass
class LstParserResponse:
    date: str = field(default="")
    object: str = field(default="")
    project: str = field(default="")
    lst_content: bytes = field(default_factory=bytes)
    map_info: LstParserResponseMap = field(default_factory=LstParserResponseMap)
    exp_info: LstParserResponseExpInfo = field(default_factory=LstParserResponseExpInfo)
