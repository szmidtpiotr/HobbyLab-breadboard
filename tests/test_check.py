import pytest

from hlbb import Board, Circuit, HlbbError, NANO, D1_MINI, UNO, check


def rc_circuit():
    """The RC filter example, with the UNO beside the board."""
    c = Circuit("RC", board=Board.MINI_170)
    r1, r2 = c.resistor("R1", "10k"), c.resistor("R2", "1k")
    c1 = c.cap_electrolytic("C1", "10uF")
    u = c.module("U1", UNO)
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
    return c, bb


def errors(c):
    return " || ".join(check(c).errors)


def test_rc_example_passes():
    c, _ = rc_circuit()
    r = check(c)
    assert r.ok, r.report()
    assert {p.label for p in r.strips["top 5"]} == {"R1.2", "R2.1", "C1.+"}


def test_missing_connection():
    c, bb = rc_circuit()
    bb.wires.pop()                      # drop the A0 wire
    e = errors(c)
    assert "sieć OUT" in e and "U1.A0" in e


def test_short_between_nets():
    c, bb = rc_circuit()
    bb.wire("e11", "d8", "red")         # OUT strip to GND strip
    assert "ZWARCIE sieci GND i OUT" in errors(c)


def test_two_ends_one_hole():
    c, bb = rc_circuit()
    bb.wire("a2", "j1", "red")          # a2 already holds R1.1
    e = errors(c)
    assert "dziurka a2 zajęta 2 razy" in e and "R1.1" in e


def test_part_shorted_on_one_strip():
    c = Circuit("x", board=Board.MINI_170)
    r = c.resistor("R1", "1k")
    c.breadboard.place(r, "a3", "d3")
    assert "element zwarty" in errors(c)


def test_module_duplicate_gnd_not_short():
    c = Circuit("x", board=Board.HALF_400)
    n = c.module("U1", NANO)
    led = c.led("D1")
    r = c.resistor("R1", "330")
    c.net("LED", n["D2"], r[1])
    c.net("A", r[2], led["A"])
    c.net("GND", led["K"], n["GND"])           # first GND, the board ties GND.2 inside
    bb = c.breadboard
    bb.place(n, "h1")                          # pin 1 (TX) at h1, pins go right, other row d
    pin_d2 = bb.hole_of(n["D2"])
    assert pin_d2.name == "h5"
    assert bb.hole_of(n["GND.2"]).name == "d2"
    bb.place(r, "j5", "j20")
    bb.place(led, "i20", "i22")
    bb.wire("j22", "B-22", "black")
    bb.wire("T-14", "a2", "black")             # a2 = GND.2 column
    bb.wire("T-28", "B-28", "black")           # join the two minus rails
    r2 = check(c)
    assert r2.ok, r2.report()


def test_unplaced_part_error():
    c = Circuit("x", board=Board.MINI_170)
    r1, r2 = c.resistor("R1", "1k"), c.resistor("R2", "1k")
    c.net("N", r1[2], r2[1])
    c.breadboard.place(r1, "a1", "a4")
    assert "R2.1 nie jest nigdzie wpięta" in errors(c)


def test_dip_pin_holes():
    c = Circuit("x", board=Board.HALF_400)
    u = c.dip("U2", "NE555", ["GND", "TRIG", "OUT", "RST", "CV", "THR", "DIS", "VCC"])
    pl = c.breadboard.place(u, "f10")          # pin 1 bottom-left, notch left
    assert [h.name for h in pl.holes] == ["f10", "f11", "f12", "f13", "e13", "e12", "e11", "e10"]
    c2 = Circuit("y", board=Board.HALF_400)
    u2 = c2.dip("U2", "NE555", ["GND", "TRIG", "OUT", "RST", "CV", "THR", "DIS", "VCC"])
    pl2 = c2.breadboard.place(u2, "e13")       # turned around: pin 1 top-right, pins go left
    assert [h.name for h in pl2.holes] == ["e13", "e12", "e11", "e10", "f10", "f11", "f12", "f13"]


def test_module_width_misfit_raises():
    c = Circuit("x", board=Board.HALF_400)
    d1 = c.module("U1", D1_MINI)
    with pytest.raises(HlbbError, match="rowkiem|poza płytkę"):
        c.breadboard.place(d1, "e8")           # 0.9" from row e -> no row there
    c2 = Circuit("y", board=Board.HALF_400)
    with pytest.raises(HlbbError, match="nie mieści się"):
        c2.breadboard.place(c2.module("U1", UNO), "a1")


def test_d1_mini_fits_a_to_h():
    c = Circuit("x", board=Board.HALF_400)
    pl = c.breadboard.place(c.module("U1", D1_MINI), "a8")
    assert pl.holes[7].name == "a1" and pl.holes[8].name == "h1"   # 5V opposite 3V3


def test_rails_continuous():
    c = Circuit("x", board=Board.HALF_400)
    r1, r2 = c.resistor("R1", "1k"), c.resistor("R2", "1k")
    c.net("V", r1[1], r2[1])
    bb = c.breadboard
    bb.place(r1, "a1", "a4")
    bb.place(r2, "a20", "a24")
    bb.wire("b1", "T+1", "red")
    bb.wire("b20", "T+29", "red")
    assert check(c).ok


def test_rail_gap_hole_rejected():
    c = Circuit("x", board=Board.HALF_400)
    with pytest.raises(HlbbError, match="nie ma dziurki"):
        c.breadboard.hole("T+6")


def test_undeclared_connection():
    c, bb = rc_circuit()
    extra = c.resistor("R9", "1M")
    bb.place(extra, "d5", "d14")               # sits in FILT strip, not declared
    assert "w opisie tego nie ma: R9.1" in errors(c)


def test_pin_alias_lookup():
    c = Circuit("x")
    d1 = c.module("U1", D1_MINI)
    assert d1["D5"].number == 4 and d1["SCK"].number == 4
    n = c.module("U2", NANO)
    assert n["GND"].number == 4 and n["GND.2"].number == 29


def test_no_breadboard_nets_are_connections():
    c = Circuit("x")
    u = c.module("U1", D1_MINI)
    r = c.resistor("R1", "330")
    c.net("DATA", u["D4"], r[1])
    assert check(c).ok
    c.net("GND", u["GND"], r[1])               # same pin in two nets
    assert "dwóch sieciach" in errors(c)


def test_cable_between_nets_is_short():
    c = Circuit("x")
    u = c.module("U1", D1_MINI)
    r = c.resistor("R1", "330")
    c.net("DATA", u["D4"], r[1])
    c.net("GND", u["GND"], r[2])
    c.cable(u["D4"], r[2], "red")
    assert "ZWARCIE" in errors(c)


def test_hole_under_module_rejected():
    c = Circuit("x", board=Board.FULL_830)
    d1 = c.module("U1", D1_MINI)
    r = c.resistor("R1", "1k")
    c.net("V", d1["3V3"], r[1])
    bb = c.breadboard
    bb.place(d1, "a10")                        # rows a and h, body covers b..g in cols 3..10
    bb.place(r, "b3", "b20")
    assert "dziurka b3 jest pod modułem U1" in errors(c)
