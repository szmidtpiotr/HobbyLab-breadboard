import os
from pathlib import Path

from hlbb.cli import main

EX = Path(__file__).resolve().parent.parent / "examples"


def test_render_example(tmp_path):
    assert main(["render", str(EX / "rc_filter.py"), "-o", str(tmp_path)]) == 0
    names = sorted(os.listdir(tmp_path))
    assert names == ["assembly.json", "breadboard-bare.svg", "breadboard.png", "breadboard.svg",
                     "check.txt", "montaz.html", "wiring.png", "wiring.svg"]
    assert "OK" in (tmp_path / "check.txt").read_text()


def test_render_broken_exits_1(tmp_path):
    src = (EX / "rc_filter.py").read_text().replace('bb.wire("d11", u["A0"], "green")\n', "")
    f = tmp_path / "broken.py"
    f.write_text(src)
    assert main(["render", str(f), "-o", str(tmp_path / "out"), "--no-png"]) == 1
    assert "sieć OUT" in (tmp_path / "out" / "check.txt").read_text()


def test_description_error_exits_2(tmp_path, capsys):
    f = tmp_path / "bad.py"
    f.write_text('from hlbb import *\nc = Circuit("x", board=Board.MINI_170)\n'
                 'c.breadboard.place(c.resistor("R1", "1k"), "a1", "z9")\n')
    assert main(["render", str(f), "-o", str(tmp_path / "o")]) == 2
    assert "Nieznana dziurka" in capsys.readouterr().err


def test_all_examples_pass(tmp_path):
    for ex in EX.glob("*.py"):
        assert main(["render", str(ex), "-o", str(tmp_path / ex.stem), "--no-png"]) == 0, ex.name


def test_doc_skeleton_is_valid_description(tmp_path):
    import re
    doc = (EX.parent / "docs" / "03-format-opisu.md").read_text()
    code = re.findall(r"```python\n(.*?)```", doc, re.S)[0]
    f = tmp_path / "skel.py"
    f.write_text(code)
    assert main(["render", str(f), "-o", str(tmp_path / "o"), "--no-png"]) in (0, 1)
