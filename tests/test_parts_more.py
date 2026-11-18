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
