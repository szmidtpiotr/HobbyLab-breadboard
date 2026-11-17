import re
from pathlib import Path

from hlbb import Board, Circuit, D1_MINI, ModuleDef
from hlbb.assembly import build_assembly, resistor_bands
from hlbb.cli import load_circuits
from hlbb.render_bb import render_breadboard

EX = Path(__file__).resolve().parent.parent / "examples"


def nano_example():
    return load_circuits(str(EX / "nano_leds_button.py"))[0]


def test_bands():
    assert resistor_bands("330 Ω") == ["pomarańczowy", "pomarańczowy", "brązowy", "złoty"]
    assert resistor_bands("10 kΩ") == ["brązowy", "czarny", "pomarańczowy", "złoty"]
    assert resistor_bands("4,7 kΩ") == ["żółty", "fioletowy", "czerwony", "złoty"]
    assert resistor_bands("4k7") == ["żółty", "fioletowy", "czerwony", "złoty"]
    assert resistor_bands("1M") == ["brązowy", "czarny", "zielony", "złoty"]
    assert resistor_bands("R?") is None


def test_order_nano_example():
    a = build_assembly(nano_example())
    groups = [s["group"] for s in a["steps"]]
    assert groups[0] == "zbierz" and groups[-1] == "kontrola"
    assert groups.index("moduly") < groups.index("niskie") < groups.index("wysokie") < groups.index("przewody")
    assert groups == sorted(groups, key=["zbierz", "moduly", "niskie", "wysokie", "przewody",
                                         "kable", "kontrola"].index)
    titles = [s["title"] for s in a["steps"]]
    assert titles[1].startswith("U1")
    led = next(s for s in a["steps"] if s["title"].startswith("LED1"))
    assert "dłuższa nóżka (+) w h22" in led["text"]
    r1 = next(s for s in a["steps"] if s["title"].startswith("R1"))
    assert "pomarańczowy – pomarańczowy – brązowy – złoty" in r1["details"][0]
    wires = [s for s in a["steps"] if s["group"] == "przewody"]
    assert len(wires) == 8
    assert "czarny" in wires[0]["title"]            # ground first, signals last
    assert "czarny" not in wires[-1]["title"]
    assert [s["n"] for s in a["steps"]] == list(range(1, len(a["steps"]) + 1))


def test_groups_exist_for_every_highlight():
    c = nano_example()
    svg = render_breadboard(c, legend=False)
    for s in build_assembly(c)["steps"]:
        for hl in s["hl"]:
            assert f'data-hl="{hl}"' in svg, hl


def test_hash_changes_with_circuit():
    a1 = build_assembly(nano_example())
    c = nano_example()
    c.breadboard.wires.pop()
    c.breadboard.wire("j4", "B-5", "black")
    assert build_assembly(c)["hash"] != a1["hash"]
    assert build_assembly(nano_example())["hash"] == a1["hash"]


def test_failed_check_has_no_steps():
    c = nano_example()
    c.breadboard.wires.pop(0)
    a = build_assembly(c)
    assert a["ok"] is False and a["steps"] == []


def test_cables_only_circuit():
    c = Circuit("x")
    d1 = c.module("U1", D1_MINI)
    ring = c.module("LED1", ModuleDef("Ring", ("5V", "GND", "DIN")))
    c.net("5V", d1["5V"], ring["5V"])
    c.net("DIN", d1["D4"], ring["DIN"])
    c.cable(d1["D4"], ring["DIN"], "green")
    a = build_assembly(c)
    cab = [s for s in a["steps"] if s["group"] == "kable"]
    assert len(cab) == 2
    assert "kablem (zielony)" in cab[1]["text"]


def test_duplicate_wires_two_steps():
    c = Circuit("x", board=Board.HALF_400)
    r1, r2 = c.resistor("R1", "1k"), c.resistor("R2", "1k")
    c.net("V", r1[1], r2[1])
    bb = c.breadboard
    bb.place(r1, "a1", "a4")
    bb.place(r2, "a20", "a24")
    bb.wire("b1", "b20", "red")
    bb.wire("c1", "c20", "red")
    a = build_assembly(c)
    w = [s for s in a["steps"] if s["group"] == "przewody"]
    assert len(w) == 2 and w[0]["hl"] != w[1]["hl"]
