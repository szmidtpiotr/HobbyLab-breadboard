"""Modules on cables, no breadboard (GlassShard-like)."""
from hlbb import *

RING = ModuleDef("Ring WS2812B", ("5V", "GND", "DIN"))
MIC = ModuleDef("Mikrofon INMP441", ("VDD", "GND", "L/R", "SCK", "WS", "SD"))

c = Circuit("XIAO ESP32-S3 + ring LED + mikrofon",
            notes="Rezystor 330 Ω lutowany w przewód danych, blisko ringu.")
x = c.module("U1", XIAO_ESP32S3)
ring = c.module("LED1", RING)
mic = c.module("MIC1", MIC)
r = c.resistor("R1", "330 Ω")

c.net("5V", x["5V"], ring["5V"])
c.net("GND", x["GND"], ring["GND"], mic["GND"], mic["L/R"])
c.net("3V3", x["3V3"], mic["VDD"])
c.net("DATA", x["D0"], r[1])
c.net("DIN", r[2], ring["DIN"])
c.net("BCLK", x["D8"], mic["SCK"], color="blue")
c.net("WS", x["D9"], mic["WS"], color="yellow")
c.net("SD", x["D10"], mic["SD"], color="green")
