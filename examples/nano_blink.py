"""Arduino Nano on a 400-hole breadboard blinking an LED on D2."""
from hlbb import *

c = Circuit("Miganie diodą LED: Arduino Nano, pin D2", board=Board.HALF_400,
            notes="Nano zasilane z USB. Minus górnej i dolnej szyny połączony przewodem w kolumnie 28.")
n = c.module("U1", NANO)
r = c.resistor("R1", "330 Ω")
led = c.led("D1", "czerwona")

c.net("D2", n["D2"], r[1])
c.net("LED_A", r[2], led["A"])
c.net("GND", led["K"], n["GND"])

bb = c.breadboard
bb.place(n, "h1")                  # pin 1 (TX) at h1, USB to the left
bb.place(r, "j5", "j20")
bb.place(led, "i20", "i22")
bb.wire("j22", "B-22", "black")
bb.wire("T-14", "a2", "black")     # Nano GND (pin 29) column
bb.wire("T-28", "B-28", "black")
