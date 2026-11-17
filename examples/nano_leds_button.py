"""Arduino Nano + two LEDs + push button on a 400-hole breadboard: lots of jumper wires."""
from hlbb import *

c = Circuit("Nano: dwie diody LED i przycisk", board=Board.HALF_400,
            notes="Przycisk na D2 z wewnętrznym podciąganiem (INPUT_PULLUP): wciśnięty = LOW.")
n = c.module("U1", NANO)
r1, r2 = c.resistor("R1", "330 Ω"), c.resistor("R2", "330 Ω")
led1, led2 = c.led("LED1", "czerwona"), c.led("LED2", "zielona")
sw = c.button("SW1")

c.net("D3", n["D3"], r1[1])
c.net("LED1_A", r1[2], led1["A"])
c.net("D4", n["D4"], r2[1])
c.net("LED2_A", r2[2], led2["A"])
c.net("BTN", n["D2"], sw["A1"])
c.net("GND", n["GND"], led1["K"], led2["K"], sw["B1"])

bb = c.breadboard
bb.place(n, "h1")                  # Nano straddles rows d/h, USB on the left
# red LED, bottom half
bb.place(r1, "g18", "g22")
bb.place(led1, "h22", "h24")
bb.wire("j6", "f18", "orange")     # D3 -> R1
bb.wire("j24", "B-23", "black")    # LED1 cathode -> bottom minus rail
# green LED, top half
bb.place(r2, "c19", "c23")
bb.place(led2, "b23", "b25")
bb.wire("i7", "e19", "green")      # D4 -> R2
bb.wire("a25", "T-25", "black")    # LED2 cathode -> top minus rail
# button across the centre gap
bb.place(sw, "e27")
bb.wire("j5", "j27", "yellow")     # D2 -> button
bb.wire("a29", "T-29", "black")    # button other side -> top minus rail
# ground from both Nano GND pins to both minus rails
bb.wire("a2", "T-2", "black")      # Nano GND (pin 29, row d)
bb.wire("j4", "B-4", "black")      # Nano GND (pin 4, row h)
