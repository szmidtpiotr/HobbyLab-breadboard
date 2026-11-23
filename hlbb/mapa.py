"""hlbb mapa: InteractiveHtmlBom assembly map with click-to-mark single parts.

Pipeline: (EasyEDA only) wrap loose pads into parts -> ibom --no-compression ->
finish_html(): Polish notes / renames from opisy.yml, 'Placed' marking, our click add-on.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from .model import HlbbError

WEB = Path(__file__).with_name("mapa_web")
MARKER = "hlbb-klik"
IBOM_LOCAL = os.environ.get("HLBB_IBOM", os.path.expanduser("~/.venvs/ibom/bin/generate_interactive_bom"))
# No default on purpose: KiCad boards are converted over SSH on your own KiCad host.
KICAD_HOST = os.environ.get("HLBB_KICAD_HOST")
IBOM_REMOTE = os.environ.get("HLBB_IBOM_REMOTE", "~/tools/InteractiveHtmlBom/InteractiveHtmlBom/generate_interactive_bom.py")

IBOM_FLAGS = [
    "--no-browser", "--no-compression", "--dark-mode", "--show-pads", "--show-silkscreen",
    "--highlight-pin1", "selected", "--redraw-on-drag", "--checkboxes", "Sourced,Placed",
    "--bom-view", "left-right", "--include-tracks", "--show-fields", "Value,Footprint",
]


def load_opisy(path: str | None) -> dict:
    if not path:
        return {}
    import yaml
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    bad = set(data) - {"tytul", "czesci", "dolacz"}
    if bad:
        raise HlbbError(f"{path}: nieznane klucze {sorted(bad)} (dozwolone: tytul, czesci, dolacz)")
    return data


# ---------- pcbdata in the uncompressed ibom HTML ----------

def _find_line(html: str, prefix: str) -> tuple[int, int]:
    start = html.find("\n" + prefix)
    if start < 0:
        raise HlbbError(f"brak '{prefix}' w HTML — ibom uruchomiony bez --no-compression?")
    start += 1
    end = html.find("\n", start)
    return start, end


def read_pcbdata(html: str) -> tuple[dict, dict]:
    s, e = _find_line(html, "var pcbdata =")
    pcbdata = json.loads(html[s + len("var pcbdata ="):e].strip().rstrip(";"))
    s, e = _find_line(html, "var config =")
    config = json.loads(html[s + len("var config ="):e].strip().rstrip(";"))
    return pcbdata, config


def _write_back(html: str, pcbdata: dict, config: dict) -> str:
    s, e = _find_line(html, "var pcbdata =")
    html = html[:s] + "var pcbdata = " + json.dumps(pcbdata, ensure_ascii=False) + html[e:]
    s, e = _find_line(html, "var config =")
    return html[:s] + "var config = " + json.dumps(config, ensure_ascii=False) + html[e:]


def apply_opisy(pcbdata: dict, config: dict, opisy: dict) -> None:
    czesci = opisy.get("czesci") or {}
    fps = pcbdata["footprints"]
    by_ref = {}
    for i, fp in enumerate(fps):
        by_ref.setdefault(fp["ref"], []).append(i)
    unknown = sorted(set(czesci) - set(by_ref))
    if unknown:
        raise HlbbError(f"opisy: tych oznaczeń nie ma na płytce: {', '.join(unknown)}")
    fields = pcbdata["bom"]["fields"]
    names = config["fields"]
    vi = names.index("Value") if "Value" in names else None
    if "Opis" not in names and any((c or {}).get("opis") for c in czesci.values()):
        names.append("Opis")
        for vals in fields.values():
            vals.append("")
    oi = names.index("Opis") if "Opis" in names else None
    renames = {}
    for ref, c in czesci.items():
        c = c or {}
        for i in by_ref[ref]:
            key = str(i)
            if c.get("opis") and oi is not None:
                fields[key][oi] = str(c["opis"])
            if c.get("wartosc") and vi is not None:
                fields[key][vi] = str(c["wartosc"])
            if c.get("ref"):
                fps[i]["ref"] = str(c["ref"])
                renames[i] = str(c["ref"])
    for side in ("both", "F", "B"):
        for row in pcbdata["bom"].get(side, []):
            for r in row:
                if r[1] in renames:
                    r[0] = renames[r[1]]
    if opisy.get("tytul"):
        pcbdata["metadata"]["title"] = str(opisy["tytul"])


def finish_html(html: str, opisy: dict) -> str:
    pcbdata, config = read_pcbdata(html)
    apply_opisy(pcbdata, config, opisy)
    config["checkboxes"] = "Sourced,Placed"
    config["mark_when_checked"] = "Placed"
    html = _write_back(html, pcbdata, config)
    js = (WEB / "klik.js").read_text(encoding="utf-8")
    css = (WEB / "klik.css").read_text(encoding="utf-8")
    addon = f'<style id="{MARKER}-css">{css}</style>\n<script id="{MARKER}">{js}</script>\n'
    i = html.rfind("</body>")
    if i < 0:
        raise HlbbError("brak </body> w HTML z ibom")
    return html[:i] + addon + html[i:]


def count_parts(pcbdata: dict) -> int:
    return len({r[1] for row in pcbdata["bom"]["both"] for r in row})


# ---------- EasyEDA: loose pads -> parts ----------

def _esc(s: str) -> str:
    return str(s).replace("~", "-").replace("`", "'").replace("#@$", "")


def wrap_easyeda_pads(doc: dict, groups: dict) -> dict:
    """groups: ref -> {wartosc, obudowa, strona: gora|dol, pady: {ksztalt, warstwa}}."""
    shapes, loose = [], []
    for s in doc["shape"]:
        (loose if s.startswith("PAD~") else shapes).append(s)
    used: set[str] = set()
    for ref, g in (groups or {}).items():
        want = g.get("pady") or {}
        pads = [s for s in loose if s not in used
                and str(want.get("ksztalt", s.split("~")[1])) == s.split("~")[1]
                and str(want.get("warstwa", s.split("~")[6])) == s.split("~")[6]]
        if not pads:
            raise HlbbError(f"dolacz {ref}: żaden luźny pad nie pasuje do {want}")
        used.update(pads)
        xs = [float(s.split("~")[2]) for s in pads]
        ys = [float(s.split("~")[3]) for s in pads]
        cx, cy = round(sum(xs) / len(xs), 3), round(sum(ys) / len(ys), 3)
        layer = "2" if g.get("strona") == "dol" else "1"
        head = f"LIB~{cx}~{cy}~package`{_esc(g.get('obudowa', ''))}`~~~gge_hlbb_{ref}~{layer}~~~0~"
        txt = lambda k, v: f"TEXT~{k}~{cx}~{cy}~0.6~0~0~3~~4.5~{_esc(v)}~~none~"  # noqa: E731
        shapes.append("#@$".join([head, txt("N", g.get("wartosc", ref)), txt("P", ref)] + pads))
    shapes.extend(s for s in loose if s not in used)
    out = dict(doc)
    out["shape"] = shapes
    return out


def _easyeda_doc(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    # accept the raw API answer too: {"result": {"dataStr": ...}}
    if "result" in d and "dataStr" in d["result"]:
        ds = d["result"]["dataStr"]
        d = json.loads(ds) if isinstance(ds, str) else ds
    if "shape" not in d:
        raise HlbbError(f"{path}: to nie jest plik płytki EasyEDA (brak 'shape')")
    return d


# ---------- running ibom ----------

def _run_ibom_local(board: str, workdir: str, layer_view: str) -> str:
    if not os.path.exists(IBOM_LOCAL):
        raise HlbbError(f"brak InteractiveHtmlBom: {IBOM_LOCAL} (python3 -m venv ~/.venvs/ibom && "
                        "~/.venvs/ibom/bin/pip install --no-deps InteractiveHtmlBom jsonschema)")
    env = dict(os.environ, INTERACTIVE_HTML_BOM_NO_DISPLAY="1")
    r = subprocess.run([IBOM_LOCAL, board, *IBOM_FLAGS, "--layer-view", layer_view,
                        "--dest-dir", workdir, "--name-format", "raw"],
                       env=env, capture_output=True, text=True)
    out = os.path.join(workdir, "raw.html")
    if r.returncode or not os.path.exists(out):
        raise HlbbError(f"InteractiveHtmlBom nie zadziałał:\n{r.stdout}{r.stderr}")
    return out


def _run_ibom_kicad(board: str, workdir: str, layer_view: str) -> str:
    if not KICAD_HOST:
        raise HlbbError("mapa dla .kicad_pcb potrzebuje zmiennej HLBB_KICAD_HOST "
                        "(np. user@kicad-host) - komputera z KiCadem 9 i InteractiveHtmlBom")
    rdir = "/tmp/hlbb-mapa"
    name = os.path.basename(board)
    sh = lambda cmd: subprocess.run(cmd, capture_output=True, text=True)  # noqa: E731
    sh(["ssh", KICAD_HOST, f"rm -rf {rdir} && mkdir -p {rdir}"])
    r = sh(["scp", "-q", board, f"{KICAD_HOST}:{rdir}/{name}"])
    if r.returncode:
        raise HlbbError(f"nie skopiowałem płytki na {KICAD_HOST}: {r.stderr}")
    flags = " ".join(f"'{f}'" for f in [*IBOM_FLAGS, "--layer-view", layer_view,
                                        "--dest-dir", rdir, "--name-format", "raw"])
    r = sh(["ssh", KICAD_HOST,
            f"INTERACTIVE_HTML_BOM_NO_DISPLAY=1 python3 {IBOM_REMOTE} {rdir}/{name} {flags}"])
    out = os.path.join(workdir, "raw.html")
    c = sh(["scp", "-q", f"{KICAD_HOST}:{rdir}/raw.html", out])
    if r.returncode or c.returncode:
        raise HlbbError(f"InteractiveHtmlBom na {KICAD_HOST} nie zadziałał:\n{r.stdout}{r.stderr}")
    return out


def mapa(board: str, opisy_path: str | None, out_dir: str | None, name: str | None,
         layer_view: str = "FB") -> str:
    opisy = load_opisy(opisy_path)
    board = os.path.abspath(board)
    stem = name or Path(board).stem
    out_dir = out_dir or os.path.join(os.path.dirname(board), "out")
    os.makedirs(out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hlbb-mapa-") as tmp:
        if board.endswith(".kicad_pcb"):
            if opisy.get("dolacz"):
                raise HlbbError("'dolacz' działa tylko dla plików EasyEDA")
            raw = _run_ibom_kicad(board, tmp, layer_view)
        elif board.endswith(".json"):
            doc = wrap_easyeda_pads(_easyeda_doc(board), opisy.get("dolacz") or {})
            src = os.path.join(tmp, stem + ".json")
            with open(src, "w", encoding="utf-8") as f:
                json.dump(doc, f)
            raw = _run_ibom_local(src, tmp, layer_view)
        else:
            raise HlbbError("płytka: .kicad_pcb (KiCad) albo .json (EasyEDA)")
        with open(raw, encoding="utf-8") as f:
            html = finish_html(f.read(), opisy)
    target = os.path.join(out_dir, f"montaz-{stem}.html")
    with open(target, "w", encoding="utf-8") as f:
        f.write(html)
    n = count_parts(read_pcbdata(html)[0])
    print(f"mapa montażu: {target} ({n} części do przylutowania)")
    return target
