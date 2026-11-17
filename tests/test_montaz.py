import json
import re
from pathlib import Path

from hlbb.cli import main

EX = Path(__file__).resolve().parent.parent / "examples"


def page_data(html):
    m = re.search(r'<script type="application/json" id="data">(.*?)</script>', html, re.S)
    return json.loads(m.group(1).replace("<\\/", "</"))


def test_montaz_page(tmp_path):
    assert main(["render", str(EX / "nano_leds_button.py"), "-o", str(tmp_path), "--no-png"]) == 0
    html = (tmp_path / "montaz.html").read_text()
    d = page_data(html)
    assert d["format"] == "hlbb-assembly" and d["ok"] and len(d["steps"]) > 10
    assert html.count("<svg") == 2 and 'data-hl="p-R1"' in html
    assert "http://" not in html.replace("http://www.w3.org/2000/svg", "")   # no network
    assert json.loads((tmp_path / "assembly.json").read_text())["hash"] == d["hash"]


def test_montaz_failed_check(tmp_path):
    src = (EX / "rc_filter.py").read_text().replace('bb.wire("d11", u["A0"], "green")\n', "")
    f = tmp_path / "broken.py"
    f.write_text(src)
    main(["render", str(f), "-o", str(tmp_path / "o"), "--no-png"])
    html = (tmp_path / "o" / "montaz.html").read_text()
    assert "nie przeszedł sprawdzenia" in html and page_data(html)["steps"] == []
    assert "<svg" not in html


def test_montaz_cables_only(tmp_path):
    assert main(["render", str(EX / "xiao_ring_mic.py"), "-o", str(tmp_path), "--no-png"]) == 0
    html = (tmp_path / "montaz.html").read_text()
    assert html.count("<svg") == 1 and page_data(html)["board"] is None
