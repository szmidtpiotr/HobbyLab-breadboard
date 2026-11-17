import os
import xml.etree.ElementTree as ET

from hlbb.png import to_png
from hlbb.render_bb import render_breadboard
from test_check import rc_circuit


def test_breadboard_svg(tmp_path):
    c, _ = rc_circuit()
    svg = render_breadboard(c)
    root = ET.fromstring(svg)
    texts = " ".join(t.text or "" for t in root.iter("{http://www.w3.org/2000/svg}text"))
    for s in ("R1 10k", "R2 1k", "C1 10uF", "U1: Arduino UNO R3", "D13", "A0",
              "Kolumna 5 góra (a–e): R1.2, R2.1, C1.+", "sieć FILT"):
        assert s in texts, s
    p_svg, p_png = tmp_path / "bb.svg", tmp_path / "bb.png"
    p_svg.write_text(svg)
    assert to_png(str(p_svg), str(p_png))
    assert os.path.getsize(p_png) > 10_000


def test_breadboard_svg_marks_failed_check():
    c, bb = rc_circuit()
    bb.wires.pop()
    assert "sprawdzenie znalazło błędy" in render_breadboard(c)


def test_wiring_svg():
    from hlbb.render_wiring import render_wiring
    c, _ = rc_circuit()
    root = ET.fromstring(render_wiring(c))
    texts = " ".join(t.text or "" for t in root.iter("{http://www.w3.org/2000/svg}text"))
    for net in ("PWM", "FILT", "GND", "OUT"):
        assert f"{net}:" in texts, net
    for pin in ("D13", "A0", "R1: 10k", "C1: 10uF"):
        assert pin in texts, pin
    assert "GND.2" not in texts                 # duplicates shown under their printed name
