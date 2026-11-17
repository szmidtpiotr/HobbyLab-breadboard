"""v2: KiCad bridge. Circuit -> design.py + generic generators (gen_sch.py, gen_pcb.py,
import_ses.py, flow.sh) that run on your own KiCad 9 host (see HLBB_KICAD_HOST)."""
from __future__ import annotations

import datetime
import os
import re
import shutil

from .model import Circuit, HlbbError, Part, Pin

TPL = os.path.join(os.path.dirname(__file__), "kicad_tpl")

# kind -> (symbol, footprint, KiCad pin number for each of our pins)
# Device:D / Device:LED: pin 1 = K, pin 2 = A. Device:C_Polarized: pin 1 = +.
# SW_PUSH_6mm: pads 1,1 (one pair) and 2,2; our A1,A2 = one side, B1,B2 = the other.
DEFAULTS = {
    "resistor": ("Device:R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", ["1", "2"]),
    "cap": ("Device:C", "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm", ["1", "2"]),
    "cap_e": ("Device:C_Polarized", "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm", ["1", "2"]),
    "diode": ("Device:D", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal", ["2", "1"]),
    "led": ("Device:LED", "LED_THT:LED_D5.0mm", ["2", "1"]),
    "button": ("Switch:SW_Push", "Button_Switch_THT:SW_PUSH_6mm", ["1", "1", "2", "2"]),
}


def slug(s: str) -> str:
    s = s.lower()
    for a, b in zip("ąćęłńóśźż", "acelnoszz"):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40].strip("-") or "circuit"


def ascii_text(s: str) -> str:
    """Silkscreen fonts are ASCII-only in practice (JLCPCB readability)."""
    for a, b in zip("ąćęłńóśźżĄĆĘŁŃÓŚŹŻΩµ", "acelnoszzACELNOSZZRu"):
        s = s.replace(a, b)
    s = s.replace("→", "->").replace("—", "-").replace("–", "-")
    return re.sub(r" +", " ", s.encode("ascii", "ignore").decode())


def kicad_part(c: Circuit, part: Part) -> dict:
    """symbol, footprint, pin map (our pin index -> KiCad number), pin labels."""
    used = sorted({p.index for n in c.nets for p in n.pins if p.part is part}
                  | {p.index for cab in c.cables for p in (cab.a, cab.b) if p.part is part})
    if part.kicad_symbol and part.kicad_footprint:
        return dict(symbol=part.kicad_symbol, footprint=part.kicad_footprint,
                    pins=[str(i + 1) for i in range(len(part.pins))], labels=None)
    if part.kind in DEFAULTS:
        sym, fp, pins = DEFAULTS[part.kind]
        return dict(symbol=sym, footprint=fp, pins=pins, labels=None)
    n = len(part.pins)
    if part.kind == "header":
        return dict(symbol=f"Connector_Generic:Conn_01x{n:02d}",
                    footprint=f"Connector_PinHeader_2.54mm:PinHeader_1x{n:02d}_P2.54mm_Vertical",
                    pins=[str(i + 1) for i in range(n)],
                    labels={str(i + 1): p.short for i, p in enumerate(part.pins)})
    if part.kind == "dip":
        w = {3: "7.62", 4: "10.16", 6: "15.24"}.get(part.width)
        if not w:
            raise HlbbError(f"{part.ref}: brak obudowy DIP o rozstawie {part.width / 10}\" — "
                            f"podaj kicad_symbol i kicad_footprint")
        return dict(symbol=f"Connector_Generic:Conn_02x{n // 2:02d}_Counter_Clockwise",
                    footprint=f"Package_DIP:DIP-{n}_W{w}mm",
                    pins=[str(i + 1) for i in range(n)], labels=None)
    if part.kind == "module":
        # No KiCad footprint for this module: put a pin header for a cable to it,
        # with only the pins the circuit uses, labelled on the silkscreen.
        k = len(used)
        if k == 0:
            return None
        pins = [None] * n
        for j, idx in enumerate(used):
            pins[idx] = str(j + 1)
        return dict(symbol=f"Connector_Generic:Conn_01x{k:02d}",
                    footprint=f"Connector_PinHeader_2.54mm:PinHeader_1x{k:02d}_P2.54mm_Vertical",
                    pins=pins, labels={str(j + 1): part.pins[idx].short for j, idx in enumerate(used)},
                    value=f"złącze do {part.value}")
    raise HlbbError(f"{part.ref}: nie wiem, jaki symbol KiCad dać elementowi typu {part.kind}")


def design_dict(c: Circuit, project: str | None = None) -> dict:
    project = project or slug(c.title)
    parts, nets = [], {}
    pin_no: dict[Pin, str] = {}
    for part in c.parts:
        k = kicad_part(c, part)
        if k is None:
            continue
        for p, num in zip(part.pins, k["pins"]):
            if num is not None:
                pin_no[p] = num
        d = dict(ref=part.ref, symbol=k["symbol"], footprint=k["footprint"],
                 value=k.get("value", part.value), sch=None, pcb=c.pcb_positions.get(part.ref))
        if k["labels"]:
            d["pin_labels"] = {num: ascii_text(lab) for num, lab in k["labels"].items()}
        parts.append(d)
    for n in c.nets:
        seen = []
        for p in n.pins:
            rp = (p.part.ref, pin_no[p])
            if rp not in seen:
                seen.append(rp)
        # module pins with the same name are tied inside the module: add their twins
        for p in list(n.pins):
            for grp in p.part.internal_groups():
                if p in grp and p.part.kind == "module":
                    for q in grp:
                        rp = (q.part.ref, pin_no.get(q))
                        if rp[1] and rp not in seen:
                            seen.append(rp)
        nets[re.sub(r"[^A-Za-z0-9_+\-./]", "_", n.name)] = seen
    return dict(PROJECT=project, TITLE=c.title, NOTES=c.notes, PARTS=parts, NETS=nets,
                SILK_TITLE=ascii_text(c.title)[:60])


def render_design_py(d: dict) -> str:
    lines = [
        '"""Generated by hlbb from the circuit description.',
        "Do not edit by hand: change circuit.py and run `hlbb kicad` again.",
        "PCB positions can be pinned in circuit.py with c.pcb_place(ref, x_mm, y_mm, rot).",
        '"""',
        f"PROJECT = {d['PROJECT']!r}",
        f"TITLE = {d['TITLE']!r}",
        f"NOTES = {d['NOTES']!r}",
        f"SILK_TITLE = {d['SILK_TITLE']!r}",
        f"DATE = {datetime.date.today().isoformat()!r}",
        f"PAPER = {'A3' if len(d['PARTS']) > 6 else 'A4'!r}",
        'KICAD_FP_DIR = "/usr/share/kicad/footprints"',
        'KICAD_SYM_DIR = "/usr/share/kicad/symbols"',
        "BOARD = None   # None = outline around the packed parts",
        "",
        "PARTS = [",
    ]
    for p in d["PARTS"]:
        lines.append(f"    {p!r},")
    lines += ["]", "", "# net name -> list of (ref, KiCad pin number)", "NETS = {"]
    for k, v in d["NETS"].items():
        lines.append(f"    {k!r}: {v!r},")
    lines += [
        "}",
        "",
        "# JLCPCB 2-layer capabilities (conservative): mm",
        "RULES = dict(track=0.3, clearance=0.2, via_dia=0.7, via_drill=0.35,",
        "             min_track=0.15, min_clearance=0.15, min_via_dia=0.5, min_drill=0.3,",
        "             copper_edge=0.3)",
        "",
        "",
        "def pin_net():",
        '    """(ref, pin) -> net name"""',
        "    m = {}",
        "    for net, pins in NETS.items():",
        "        for rp in pins:",
        "            m[rp] = net",
        "    return m",
        "",
    ]
    return "\n".join(lines)


def export(c: Circuit, out_dir: str, project: str | None = None) -> str:
    os.makedirs(out_dir, exist_ok=True)
    d = design_dict(c, project)
    with open(os.path.join(out_dir, "design.py"), "w") as f:
        f.write(render_design_py(d))
    for name in ("gen_sch.py", "gen_pcb.py", "import_ses.py", "flow.sh"):
        shutil.copy(os.path.join(TPL, name), os.path.join(out_dir, name))
    os.chmod(os.path.join(out_dir, "flow.sh"), 0o755)
    with open(os.path.join(out_dir, ".gitignore"), "w") as f:
        f.write("out/*.dsn\nout/*.ses\nout/*.log\nout/*.kicad_prl\nout/gerber/\n__pycache__/\n")
    return d["PROJECT"]
