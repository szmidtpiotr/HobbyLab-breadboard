from hlbb import Board, Circuit, D1_MINI, NANO, XIAO_ESP32S3, ModuleDef
from hlbb.cli import main
from hlbb.kicad import design_dict, export, slug


def test_slug_and_pin_mapping():
    c = Circuit("Miganie diodą LED")
    n = c.module("U1", NANO)
    led = c.led("D1")
    r = c.resistor("R1", "330")
    c.net("D2", n["D2"], r[1])
    c.net("A", r[2], led["A"])
    c.net("GND", led["K"], n["GND"])
    d = design_dict(c)
    assert d["PROJECT"] == slug("Miganie diodą LED") == "miganie-dioda-led"
    assert d["NETS"]["D2"] == [("U1", "5"), ("R1", "1")]
    assert d["NETS"]["A"] == [("R1", "2"), ("D1", "2")]          # LED anode = KiCad pin 2
    assert ("D1", "1") in d["NETS"]["GND"] and ("U1", "29") in d["NETS"]["GND"]   # twin GND pin
    parts = {p["ref"]: p for p in d["PARTS"]}
    assert parts["U1"]["footprint"] == "Module:Arduino_Nano"
    assert parts["D1"]["symbol"] == "Device:LED"


def test_module_without_footprint_becomes_header():
    c = Circuit("x")
    x = c.module("U1", XIAO_ESP32S3)
    ring = c.module("LED1", ModuleDef("Ring", ("5V", "GND", "DIN")))
    c.net("5V", x["5V"], ring["5V"])
    c.net("DIN", x["D0"], ring["DIN"])
    d = design_dict(c)
    u1 = next(p for p in d["PARTS"] if p["ref"] == "U1")
    assert u1["symbol"] == "Connector_Generic:Conn_01x02"
    assert u1["pin_labels"] == {"1": "D0", "2": "5V"}
    assert d["NETS"]["DIN"] == [("U1", "1"), ("LED1", "2")]


def test_dip_and_button_defaults():
    c = Circuit("x")
    u = c.dip("U1", "NE555", ["GND", "TRIG", "OUT", "RST", "CV", "THR", "DIS", "VCC"])
    sw = c.button("SW1")
    c.net("T", u["TRIG"], sw["A1"])
    d = design_dict(c)
    parts = {p["ref"]: p for p in d["PARTS"]}
    assert parts["U1"]["footprint"] == "Package_DIP:DIP-8_W7.62mm"
    assert d["NETS"]["T"] == [("U1", "2"), ("SW1", "1")]


def test_kicad_cli_refuses_failed_check(tmp_path):
    f = tmp_path / "bad.py"
    f.write_text('from hlbb import *\nc = Circuit("x", board=Board.MINI_170)\n'
                 'r = c.resistor("R1", "1k"); r2 = c.resistor("R2", "1k")\n'
                 'c.net("N", r[2], r2[1])\nc.breadboard.place(r, "a1", "a4")\n'
                 'c.breadboard.place(r2, "a6", "a9")\n')
    assert main(["kicad", str(f), "-o", str(tmp_path / "pcb")]) == 1
    assert not (tmp_path / "pcb").exists()


def test_export_writes_generators(tmp_path):
    c = Circuit("x")
    d1 = c.module("U1", D1_MINI)
    r = c.resistor("R1", "1k")
    c.net("N", d1["D4"], r[1])
    export(c, str(tmp_path))
    for f in ("design.py", "gen_sch.py", "gen_pcb.py", "import_ses.py", "flow.sh"):
        assert (tmp_path / f).exists(), f
    ns = {}
    exec((tmp_path / "design.py").read_text(), ns)
    assert ns["pin_net"]()[("U1", "11")] == "N"


def test_run_without_host_refuses(tmp_path, monkeypatch):
    monkeypatch.delenv("HLBB_KICAD_HOST", raising=False)
    c = Circuit("x")
    d1 = c.module("U1", D1_MINI)
    r = c.resistor("R1", "1k")
    c.net("N", d1["D4"], r[1])
    f = tmp_path / "ok.py"
    f.write_text('from hlbb import *\nc = Circuit("x")\nd1 = c.module("U1", D1_MINI)\n'
                 'r = c.resistor("R1", "1k")\nc.net("N", d1["D4"], r[1])\n')
    import importlib
    import hlbb.cli as cli_mod
    importlib.reload(cli_mod)
    assert cli_mod.main(["kicad", str(f), "-o", str(tmp_path / "pcb"), "--run"]) == 2
