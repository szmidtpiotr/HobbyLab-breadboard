"""PWM + RC filter on the mini breadboard, UNO beside it."""
from hlbb import *

c = Circuit("Filtr RC: PWM z D13 → napięcie na A0", board=Board.MINI_170,
            notes="Arduino UNO leży obok płytki; przewody idą do gniazd UNO.")
u = c.module("U1", UNO)
r1, r2 = c.resistor("R1", "10 kΩ"), c.resistor("R2", "1 kΩ")
c1 = c.cap_electrolytic("C1", "10 µF")

c.net("PWM", u["D13"], r1[1])
c.net("FILT", r1[2], c1["+"], r2[1])
c.net("GND", u["GND"], c1["-"])
c.net("OUT", r2[2], u["A0"])

bb = c.breadboard
bb.place(r1, "a2", "a5")
bb.place(r2, "b5", "b11")
bb.place(c1, "e5", "e8")
bb.wire("e2", u["D13"], "orange")
bb.wire("c8", u["GND"], "black")
bb.wire("d11", u["A0"], "green")
