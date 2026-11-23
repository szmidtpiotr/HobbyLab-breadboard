import json
import os
import shutil

import pytest

from hlbb.cli import main
from hlbb.mapa import MARKER, apply_opisy, finish_html, read_pcbdata, wrap_easyeda_pads
from hlbb.model import HlbbError

HERE = os.path.dirname(__file__)
FIX = os.path.join(HERE, "fixtures", "mapa")
RX = os.path.join(FIX, "rx_nano_v1.2_easyeda.json")
RX_OPISY = os.path.join(FIX, "rx_nano_opisy.yml")
needs_rx = pytest.mark.skipif(not os.path.exists(RX), reason="put an EasyEDA board + opisy.yml in tests/fixtures/mapa/ to run this")
IBOM = os.environ.get("HLBB_IBOM", os.path.expanduser("~/.venvs/ibom/bin/generate_interactive_bom"))


def tiny():
    pcbdata = {
        "footprints": [{"ref": "C1"}, {"ref": "C2"}, {"ref": "XO"}],
        "bom": {"both": [[["C1", 0], ["C2", 1]], [["XO", 2]]], "F": [[["C1", 0], ["C2", 1]]],
                "B": [[["XO", 2]]], "skipped": [],
                "fields": {"0": ["100nF", "C0402"], "1": ["100nF", "C0402"], "2": ["XO", ""]}},
        "metadata": {"title": "t", "revision": ""},
    }
    return pcbdata, {"fields": ["Value", "Footprint"]}


def test_unknown_ref_is_an_error():
    p, c = tiny()
    with pytest.raises(HlbbError, match="NOPE"):
        apply_opisy(p, c, {"czesci": {"NOPE": {"opis": "x"}}})


def test_rename_and_value_and_opis():
    p, c = tiny()
    apply_opisy(p, c, {"tytul": "Płytka", "czesci": {
        "XO": {"ref": "Y1", "wartosc": "52 MHz", "opis": "kwarc"}, "C1": {"opis": "odsprzęganie"}}})
    assert c["fields"] == ["Value", "Footprint", "Opis"]
    assert p["footprints"][2]["ref"] == "Y1"
    assert p["bom"]["both"][1] == [["Y1", 2]] and p["bom"]["B"][0] == [["Y1", 2]]
    assert p["bom"]["fields"]["2"] == ["52 MHz", "", "kwarc"]
    assert p["bom"]["fields"]["1"] == ["100nF", "C0402", ""]
    assert p["metadata"]["title"] == "Płytka"


def test_finish_html_injects_addon_and_placed_marking():
    p, c = tiny()
    html = ("<html><head></head><body>\nvar config = " + json.dumps(c) + "\nvar pcbdata = "
            + json.dumps(p) + "\n</body></html>")
    out = finish_html(html, {"czesci": {"C1": {"opis": "a"}}})
    p2, c2 = read_pcbdata(out)
    assert MARKER in out and out.index(MARKER) < out.index("</body>")
    assert c2["mark_when_checked"] == "Placed" and c2["checkboxes"] == "Sourced,Placed"
    assert p2["bom"]["fields"]["0"][2] == "a"


@needs_rx
def test_wrap_easyeda_pads_collects_matching_pads():
    with open(RX) as f:
        doc = json.load(f)
    out = wrap_easyeda_pads(doc, {"U2": {"wartosc": "ESP-01F", "obudowa": "ESP-01F", "strona": "dol",
                                         "pady": {"ksztalt": "RECT", "warstwa": 2}}})
    lib = [s for s in out["shape"] if "gge_hlbb_U2" in s]
    assert len(lib) == 1 and lib[0].count("#@$PAD~") == 18
    assert lib[0].split("~")[7] == "2"
    with pytest.raises(HlbbError):
        wrap_easyeda_pads(doc, {"X": {"pady": {"ksztalt": "OVAL", "warstwa": 7}}})


@pytest.mark.skipif(not os.path.exists(IBOM), reason="InteractiveHtmlBom not installed")
@needs_rx
def test_cli_mapa_easyeda(tmp_path):
    rc = main(["mapa", RX, "--opisy", RX_OPISY, "-o", str(tmp_path), "--nazwa", "rx"])
    assert rc == 0
    html = (tmp_path / "montaz-rx.html").read_text()
    p, c = read_pcbdata(html)
    refs = sorted(fp["ref"] for fp in p["footprints"])
    assert {"U2", "J1", "J2", "Y1", "JP1"} <= set(refs) and "XOLARGE" not in refs
    assert len({r[1] for row in p["bom"]["both"] for r in row}) == 18
    assert "nets" not in p and MARKER in html
