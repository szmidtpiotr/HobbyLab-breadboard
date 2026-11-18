"""Fuse, TO-92 (transistor / sensor), potentiometer, bidirectional diode, kind_pl."""
import pytest

from hlbb import Board, Circuit, HlbbError, check
from hlbb.assembly import build_assembly
from hlbb.kicad import design_dict
from hlbb.render_bb import render_breadboard


def demo():
    c = Circuit("x", board=Board.HALF_400)
    f1 = c.fuse("F1", "PTC 50 mA")
    q1 = c.transistor("Q1", "BC547B")                     # C, B, E seen from the flat face
    u5 = c.to92("U5", "DS18B20", ["GND", "DQ", "VDD"])
    rv = c.pot("RV1", "10 kΩ")
    d1 = c.diode("D1", "P6KE33CA", bidirectional=True, kind_pl="dioda TVS")
    br = c.dip("BR1", "DB107", ["~A", "~B", "+", "-"], kind_pl="mostek prostowniczy")
    c.net("IN", f1[2], d1["A"])
    c.net("B", q1["B"], rv["W"])
    bb = c.breadboard
    bb.place(f1, "a2", "a4")
    bb.place(d1, "b4", "b8")
    bb.place(q1, "c12")
    bb.place(rv, "h11")
    bb.wire("j12", "a13", "blue")              # wiper (col 12, bottom) -> base (col 13, top)
    bb.place(u5, "a20")
    bb.place(br, "f25")
    return c


def test_new_kinds_place_and_check():
    c = demo()
    r = check(c)
    assert r.ok, r.report()
    pl = c.breadboard.placement_of(c.parts[1])
    assert [h.name for h in pl.holes] == ["c12", "c13", "c14"]


def test_inline_needs_one_hole_not_on_rail():
    c = Circuit("x", board=Board.HALF_400)
    q = c.transistor("Q1", "BC547B")
    with pytest.raises(HlbbError, match="jedną dziurkę"):
        c.breadboard.place(q, "a1", "a2")
    with pytest.raises(HlbbError, match="szynę"):
        c.breadboard.place(q, "T+1")


def test_to92_needs_three_pins():
    with pytest.raises(HlbbError, match="3 nóżki"):
        Circuit("x").to92("U1", "X", ["A", "B"])


def test_steps_and_names():
    a = build_assembly(demo())
    steps = {s["title"].split(":")[0]: s for s in a["steps"] if s["hl"]}
    assert "Kierunek obojętny" in steps["F1"]["text"] and steps["F1"]["group"] == "niskie"
    assert "płaską stroną z napisem do siebie: C w c12, B w c13, E w c14" in steps["Q1"]["text"]
    assert steps["Q1"]["title"] == "Q1: tranzystor BC547B"
    assert steps["U5"]["title"].startswith("U5: element w obudowie TO-92")
    assert "suwak" in steps["RV1"]["text"]
    assert "dwukierunkowa" in steps["D1"]["text"] and steps["D1"]["title"] == "D1: dioda TVS P6KE33CA"
    assert steps["BR1"]["title"] == "BR1: mostek prostowniczy DB107"
    kinds = {p["ref"]: p["kind_pl"] for p in a["parts"]}
    assert kinds["F1"] == "bezpiecznik" and kinds["RV1"] == "potencjometr"


def test_plain_diode_text_unchanged():
    c = Circuit("x", board=Board.HALF_400)
    d = c.diode("D1", "1N4148")
    c.breadboard.place(d, "a1", "a5")
    s = [x for x in build_assembly(c)["steps"] if x["hl"]][0]
    assert s["text"] == "Wepnij diodę: anoda w a1, katoda (strona z paskiem) w a5."


def test_drawing_has_groups():
    svg = render_breadboard(demo(), legend=False)
    for ref in ("F1", "Q1", "U5", "RV1", "D1", "BR1"):
        assert f'data-hl="p-{ref}"' in svg, ref


def test_kicad_defaults():
    d = design_dict(demo())
    parts = {p["ref"]: p for p in d["PARTS"]}
    assert parts["F1"]["symbol"] == "Device:Polyfuse"
    assert parts["RV1"]["symbol"] == "Device:R_Potentiometer"
    assert parts["Q1"]["footprint"] == "Package_TO_SOT_THT:TO-92_Inline"
    assert parts["Q1"]["pin_labels"] == {"1": "C", "2": "B", "3": "E"}
    assert parts["D1"]["symbol"] == "Device:D_TVS"
    assert d["NETS"]["B"] == [("Q1", "2"), ("RV1", "2")]


def test_led_rgb_common_anode():
    c = Circuit("x", board=Board.HALF_400)
    led = c.led_rgb("LED1", "5 mm")
    r = c.resistor("R1", "330 Ω")
    c.net("RED", led["R"], r[1])
    bb = c.breadboard
    bb.place(led, "a10")
    bb.place(r, "b10", "b16")
    assert check(c).ok
    s = [x for x in build_assembly(c)["steps"] if x["title"].startswith("LED1")][0]
    assert s["text"] == ("Wepnij diodę RGB 5 mm (LED1): czerwona w a10, najdłuższa (wspólna "
                         "anoda, +) w a11, zielona w a12, niebieska w a13.")
    assert 'data-hl="p-LED1"' in render_breadboard(c, legend=False)
    d = design_dict(c)
    p = {x["ref"]: x for x in d["PARTS"]}["LED1"]
    assert p["symbol"] == "Device:LED_RAGB" and p["footprint"] == "LED_THT:LED_D5.0mm-4_RGB"
    assert d["NETS"]["RED"][0] == ("LED1", "1")


def test_led_rgb_common_cathode_and_errors():
    c = Circuit("x")
    led = c.led_rgb("LED1", common="K")
    c.net("GND", led["K"], c.resistor("R1", "1k")[1])
    assert {x["ref"]: x for x in design_dict(c)["PARTS"]}["LED1"]["symbol"] == "Device:LED_RKGB"
    with pytest.raises(HlbbError):
        Circuit("y").led_rgb("LED2", common="X")


def demo2():
    c = Circuit("Nowe elementy 2", board=Board.HALF_400)
    reg = c.to220("U1", "L7805CV", ["IN", "GND", "OUT"], kind_pl="stabilizator")
    bz = c.buzzer("BZ1", "SFM-27")
    mic = c.microphone("MK1")
    ph = c.ldr("R1", "GL5539")
    j1 = c.terminal("J1", 2, names=["+12V", "GND"])
    c.net("VIN", j1["+12V"], reg["IN"])
    c.net("GND", j1["GND"], reg["GND"], bz["-"])
    c.net("OUT", reg["OUT"], bz["+"])
    bb = c.breadboard
    bb.place(j1, "a2")                 # +12V a2, GND a4
    bb.place(reg, "c8")                # IN c8, GND c9, OUT c10
    bb.wire("b2", "b8", "red")
    bb.wire("e4", "e9", "black")
    bb.place(bz, "a10", "a14")
    bb.wire("d9", "d14", "black")      # buzzer minus to GND... (also joins a14 strip)
    bb.place(mic, "h20", "h22")
    bb.place(ph, "h25", "h28")
    return c


def test_more_kinds_check_steps_kicad():
    c = demo2()
    assert check(c).ok, check(c).report()
    pl = c.breadboard.placement_of(c.parts[4])
    assert [h.name for h in pl.holes] == ["a2", "a4"]              # terminal: every 2nd column
    st = {s["title"].split(":")[0]: s for s in build_assembly(c)["steps"] if s["hl"]}
    assert st["U1"]["title"] == "U1: stabilizator L7805CV"
    assert "napisem do siebie, metalową płytką od siebie: IN w c8, GND w c9, OUT w c10" in st["U1"]["text"]
    assert st["BZ1"]["text"] == "Wepnij brzęczyk: plus (+) w a10, minus (−) w a14."
    assert "obudową" in st["MK1"]["details"][0]
    assert "Kierunek obojętny" in st["R1"]["text"]
    assert "co drugą kolumnę" in st["J1"]["details"][0]
    svg = render_breadboard(c, legend=False)
    for ref in ("U1", "BZ1", "MK1", "R1", "J1"):
        assert f'data-hl="p-{ref}"' in svg
    parts = {p["ref"]: p for p in design_dict(c)["PARTS"]}
    assert parts["U1"]["footprint"] == "Package_TO_SOT_THT:TO-220-3_Vertical"
    assert parts["BZ1"]["symbol"] == "Device:Buzzer"
    assert parts["MK1"]["symbol"] == "Device:Microphone_Condenser"
    assert parts["R1"]["symbol"] == "Device:R_Photo"
    assert parts["J1"]["footprint"].endswith("MX126-5.0-02P_1x02_P5.00mm")
    assert parts["J1"]["pin_labels"] == {"1": "+12V", "2": "GND"}


def test_more_kinds_errors():
    with pytest.raises(HlbbError, match="TO-220 ma 3"):
        Circuit("x").to220("U1", "X", ["A"])
    c = Circuit("y")
    c.net("N", c.terminal("J1", 8)["1"], c.resistor("R1", "1k")[1])
    with pytest.raises(HlbbError, match="1x8"):
        design_dict(c)
