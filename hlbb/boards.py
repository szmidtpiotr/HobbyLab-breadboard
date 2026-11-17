"""Ready-made module definitions.

Pin order = KiCad symbol numbering, which for these modules is DIP
counter-clockwise (verified against KiCad 9's own symbol + footprint libraries:
MCU_Module:Arduino_Nano_v2.x + Module:Arduino_Nano footprint,
RF_Module:WEMOS_D1_mini + WEMOS_D1_mini_light footprint, MCU_Module:Arduino_UNO_R3).
A pin can be addressed by any part of a slash name: nano["D13"], d1["D5"], d1["SCK"].
"""
from .model import ModuleDef

NANO = ModuleDef(
    "Arduino Nano",
    ("D1/TX", "D0/RX", "RST", "GND", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9",
     "D10", "D11", "D12",
     "D13", "3V3", "AREF", "A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "5V", "RST",
     "GND", "VIN"),
    width=6,
    kicad_symbol="MCU_Module:Arduino_Nano_v3.x",
    kicad_footprint="Module:Arduino_Nano",
)

UNO = ModuleDef(
    "Arduino UNO R3",
    ("NC", "IOREF", "RST", "3V3", "5V", "GND", "GND", "VIN", "A0", "A1", "A2", "A3",
     "SDA/A4", "SCL/A5", "D0/RX", "D1/TX", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9",
     "D10", "D11", "D12", "D13", "GND", "AREF", "SDA/A4", "SCL/A5"),
    width=None,
    kicad_symbol="MCU_Module:Arduino_UNO_R3",
    kicad_footprint="Module:Arduino_UNO_R3",
)

D1_MINI = ModuleDef(
    "WeMos D1 mini",
    ("RST", "A0", "D0", "SCK/D5", "MISO/D6", "MOSI/D7", "CS/D8", "3V3",
     "5V", "GND", "D4", "D3", "SDA/D2", "SCL/D1", "RX", "TX"),
    width=9,
    kicad_symbol="RF_Module:WEMOS_D1_mini",
    kicad_footprint="RF_Module:WEMOS_D1_mini_light",
)

# Pin rows not verified against a footprint -> drawn beside the breadboard.
XIAO_ESP32S3 = ModuleDef(
    "XIAO ESP32-S3",
    ("D0/GPIO1", "D1/GPIO2", "D2/GPIO3", "D3/GPIO4", "D4/GPIO5/SDA", "D5/GPIO6/SCL",
     "D6/GPIO43/TX",
     "D7/GPIO44/RX", "D8/GPIO7/SCK", "D9/GPIO8/MISO", "D10/GPIO9/MOSI", "3V3", "GND", "5V"),
    width=None,
)

# Espressif ESP32-S3-DevKitC-1: J1 pins 1..22, then J3 pins 22..1.
_J1 = ("3V3", "3V3", "RST", "GPIO4", "GPIO5", "GPIO6", "GPIO7", "GPIO15", "GPIO16",
       "GPIO17", "GPIO18", "GPIO8", "GPIO3", "GPIO46", "GPIO9", "GPIO10", "GPIO11",
       "GPIO12", "GPIO13", "GPIO14", "5V", "GND")
_J3 = ("GND", "TX/GPIO43", "RX/GPIO44", "GPIO1", "GPIO2", "GPIO42", "GPIO41", "GPIO40",
       "GPIO39", "GPIO38", "GPIO37", "GPIO36", "GPIO35", "GPIO0", "GPIO45", "GPIO48",
       "GPIO47", "GPIO21", "GPIO20", "GPIO19", "GND", "GND")
ESP32_S3_DEVKITC = ModuleDef("ESP32-S3-DevKitC-1", _J1 + tuple(reversed(_J3)), width=None)

ALL = {"NANO": NANO, "UNO": UNO, "D1_MINI": D1_MINI, "XIAO_ESP32S3": XIAO_ESP32S3,
       "ESP32_S3_DEVKITC": ESP32_S3_DEVKITC}
