"""hlbb: one short circuit description -> breadboard picture,
module wiring picture, strict connection check, step-by-step assembly page,
and (optionally) a KiCad schematic + PCB."""
from .model import Circuit, HlbbError, ModuleDef, Pin, Part
from .breadboard import Board
from .boards import NANO, UNO, D1_MINI, XIAO_ESP32S3, ESP32_S3_DEVKITC
from .check import check

__all__ = ["Circuit", "HlbbError", "ModuleDef", "Pin", "Part", "Board", "check",
           "NANO", "UNO", "D1_MINI", "XIAO_ESP32S3", "ESP32_S3_DEVKITC"]
__version__ = "1.0.0"
