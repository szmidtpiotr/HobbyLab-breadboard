#!/usr/bin/env python3
"""Generate <project>.kicad_sch from design.py using KiCad's own symbol libraries.

Generic, reusable version shipped with hlbb.
Strategy: every connected pin gets a short stub wire plus a net label; unused
pins get a no-connect marker; a PWR_FLAG goes on every net that has power-input
pins but nothing driving it, so ERC is clean. Parts without a fixed "sch"
position are packed on the sheet by their pin extents.
Output is a self-contained KiCad 9 schematic (symbols embedded in lib_symbols).
"""
import math
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D  # noqa: E402

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))


# ---------- tiny S-expression reader (enough for .kicad_sym) ----------
def tokenize(s):
    tok, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1
        elif c in "()":
            tok.append(c); i += 1
        elif c == '"':
            j = i + 1
            while s[j] != '"':
                j += 2 if s[j] == "\\" else 1
            tok.append(s[i:j + 1]); i = j + 1
        else:
            j = i
            while j < n and not s[j].isspace() and s[j] not in "()":
                j += 1
            tok.append(s[i:j]); i = j
    return tok


def parse(tok, i=0):
    assert tok[i] == "("
    out, i = [], i + 1
    while tok[i] != ")":
        if tok[i] == "(":
            node, i = parse(tok, i)
            out.append(node)
        else:
            out.append(tok[i]); i += 1
    return out, i + 1


def dump(node, ind=0):
    if isinstance(node, str):
        return node
    flat = all(isinstance(x, str) for x in node)
    if flat:
        return "(" + " ".join(node) + ")"
    parts = []
    for x in node:
        if isinstance(x, str):
            parts.append(x)
    s = "(" + " ".join(parts)
    for x in node:
        if not isinstance(x, str):
            s += "\n" + "  " * (ind + 1) + dump(x, ind + 1)
    return s + ")"


def unq(s):
    return s[1:-1] if s.startswith('"') else s


def load_symbol(lib, name):
    """Return the parsed (symbol "name" ...) node from a KiCad library."""
    path = os.path.join(D.KICAD_SYM_DIR, lib + ".kicad_sym")
    text = open(path, encoding="utf-8").read()
    key = '(symbol "%s"' % name
    i = text.index(key)
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                break
    node, _ = parse(tokenize(text[i:j + 1]))
    # resolve "extends" (derived symbols) by loading the parent and renaming
    for x in node:
        if isinstance(x, list) and x[0] == "extends":
            parent = load_symbol(lib, unq(x[1]))
            props = {unq(p[1]): p for p in node if isinstance(p, list) and p[0] == "property"}
            for k, p in enumerate(parent):
                if isinstance(p, list) and p[0] == "property" and unq(p[1]) in props:
                    parent[k] = props[unq(p[1])]
            parent[1] = '"%s"' % name
            for k, p in enumerate(parent):
                if isinstance(p, list) and p[0] == "symbol":
                    p[1] = '"%s"' % re.sub(r'^"?%s' % re.escape(unq(x[1])), name, unq(p[1]))
            return parent
    return node


def symbol_pins(node):
    """Yield dict(number, name, x, y, angle, length, type) for every pin (lib coords, y up)."""
    for unit in node:
        if isinstance(unit, list) and unit[0] == "symbol":
            for p in unit:
                if isinstance(p, list) and p[0] == "pin":
                    d = dict(type=p[1])
                    for a in p:
                        if isinstance(a, list):
                            if a[0] == "at":
                                d["x"], d["y"], d["angle"] = float(a[1]), float(a[2]), float(a[3])
                            elif a[0] == "length":
                                d["length"] = float(a[1])
                            elif a[0] == "name":
                                d["name"] = unq(a[1])
                            elif a[0] == "number":
                                d["number"] = unq(a[1])
                    yield d


def rot(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def pin_sheet_pos(pin, place):
    """Connection point of a pin on the sheet + outward unit vector (sheet coords, y down)."""
    px, py, prot = place
    # library coords are y-up; sheet is y-down
    lx, ly = rot(pin["x"], pin["y"], prot)
    # outward direction: opposite to the pin's angle (angle points toward body)
    ox, oy = rot(-math.cos(math.radians(pin["angle"])), -math.sin(math.radians(pin["angle"])), prot)
    return px + lx, py - ly, ox, -oy


def f(v):
    return ("%.4f" % v).rstrip("0").rstrip(".")


G = 2.54


def snap(v):
    return round(v / G) * G


def pack_positions(parts_pins):
    """Shelf-pack symbols without a fixed position. parts_pins: [(part, pins)]."""
    paper_w, paper_h = (420.0, 297.0) if D.PAPER == "A3" else (297.0, 210.0)
    x, y, row_h = 25.4, 30.48, 0.0
    for part, pins in parts_pins:
        if part.get("sch"):
            continue
        xs = [p["x"] for p in pins] or [0]
        ys = [p["y"] for p in pins] or [0]
        pad = 12.7                          # stub + label + reference text
        w = max(xs) - min(xs) + 2 * pad + 10.16
        h = max(ys) - min(ys) + 2 * pad
        if x + w > paper_w - 20:
            x, y, row_h = 25.4, y + row_h + 5.08, 0.0
        # origin so that the symbol's pin extent starts at (x, y); lib y is up
        part["sch"] = (snap(x + pad - min(xs) + 5.08), snap(y + pad + max(ys)), 0)
        x += w + 5.08
        row_h = max(row_h, h)


def main():
    pin2net = D.pin_net()
    root_uuid = str(uuid.uuid4())
    lib_symbols, symbols, wires, labels, noconns = [], [], [], [], []
    seen_lib = set()
    net_types = {}

    def label_at(net, x, y, ox, oy):
        ang = 0 if ox > 0.5 else 180 if ox < -0.5 else 90 if oy < -0.5 else 270
        just = "left" if ang in (0, 90) else "right"
        labels.append(
            '(label "%s" (at %s %s %d) (fields_autoplaced yes)\n'
            '    (effects (font (size 1.27 1.27)) (justify %s bottom))\n'
            '    (uuid "%s"))' % (net, f(x), f(y), ang, just, uuid.uuid4()))

    loaded = []
    for part in D.PARTS:
        lib, sym = part["symbol"].split(":")
        node = load_symbol(lib, sym)
        pins = list(symbol_pins(node))
        loaded.append((part, node, pins))
    pack_positions([(p, pins) for p, _, pins in loaded])

    for part, node, pins in loaded:
        lib_id = part["symbol"]
        node[1] = '"%s"' % lib_id
        if lib_id not in seen_lib:            # keep the library copy untouched (ERC lib_symbol_mismatch)
            lib_symbols.append(dump(node, 1))
            seen_lib.add(lib_id)

        sx, sy, srot = part["sch"]
        pin_lines = "".join('\n    (pin "%s" (uuid "%s"))' % (p["number"], uuid.uuid4()) for p in pins)
        ys = [p["y"] for p in pins] or [0]
        symbols.append(
            '(symbol (lib_id "%s") (at %s %s %d) (unit 1)\n'
            '    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)\n'
            '    (uuid "%s")\n'
            '    (property "Reference" "%s" (at %s %s 0) (effects (font (size 1.27 1.27))))\n'
            '    (property "Value" "%s" (at %s %s 0) (effects (font (size 1.27 1.27))))\n'
            '    (property "Footprint" "%s" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
            '    (property "Datasheet" "" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes)))%s\n'
            '    (instances (project "%s" (path "/%s" (reference "%s") (unit 1)))))'
            % (lib_id, f(sx), f(sy), srot, uuid.uuid4(), part["ref"], f(sx), f(sy - max(ys) - 6),
               part["value"].replace('"', "'"), f(sx), f(sy - min(ys) + 6),
               part["footprint"], f(sx), f(sy), f(sx), f(sy), pin_lines, D.PROJECT, root_uuid, part["ref"]))

        for p in pins:
            x, y, ox, oy = pin_sheet_pos(p, part["sch"])
            net = pin2net.get((part["ref"], p["number"]))
            if net is None:
                if p["type"] != "no_connect":
                    noconns.append('(no_connect (at %s %s) (uuid "%s"))' % (f(x), f(y), uuid.uuid4()))
                continue
            net_types.setdefault(net, set()).add(p["type"])
            x2, y2 = x + ox * 2.54, y + oy * 2.54
            wires.append('(wire (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type default)) (uuid "%s"))'
                         % (f(x), f(y), f(x2), f(y2), uuid.uuid4()))
            label_at(net, x2, y2, ox, oy)

    # PWR_FLAG on every net with power inputs and no driver (ERC "power pin not driven")
    flagged = [n for n, t in sorted(net_types.items()) if "power_in" in t and "power_out" not in t]
    if flagged:
        flag = load_symbol("power", "PWR_FLAG")
        flag[1] = '"power:PWR_FLAG"'
        lib_symbols.append(dump(flag, 1))
    paper_h = 297.0 if D.PAPER == "A3" else 210.0
    for i, net in enumerate(flagged):
        fx, fy = snap(25.4 + i * 22.86), snap(paper_h - 30)
        symbols.append(
            '(symbol (lib_id "power:PWR_FLAG") (at %s %s 0) (unit 1)\n'
            '    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (uuid "%s")\n'
            '    (property "Reference" "#FLG%02d" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
            '    (property "Value" "PWR_FLAG" (at %s %s 0) (effects (font (size 1.27 1.27))))\n'
            '    (property "Footprint" "" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
            '    (property "Datasheet" "~" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
            '    (pin "1" (uuid "%s"))\n'
            '    (instances (project "%s" (path "/%s" (reference "#FLG%02d") (unit 1)))))'
            % (f(fx), f(fy), uuid.uuid4(), i + 1, f(fx), f(fy - 5), f(fx), f(fy - 3.5), f(fx), f(fy),
               f(fx), f(fy), uuid.uuid4(), D.PROJECT, root_uuid, i + 1))
        wires.append('(wire (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type default)) (uuid "%s"))'
                     % (f(fx), f(fy), f(fx), f(fy + 2.54), uuid.uuid4()))
        label_at(net, fx, fy + 2.54, 0, 1)

    def q(s):
        return s.replace("\\", "\\\\").replace('"', "'")

    title = ('(title_block (title "%s") (date "%s") (rev "A")\n'
             '    (comment 1 "generated by hlbb"))'
             % (q(D.TITLE), D.DATE))
    text = ""
    if D.NOTES:
        text = ('(text "%s"\n    (exclude_from_sim no) (at 25.4 %s 0) (effects (font (size 1.5 1.5)) '
                '(justify left bottom))\n    (uuid "%s"))'
                % (q(D.NOTES).replace("\n", "\\n"), f(paper_h - 12), uuid.uuid4()))

    sch = ('(kicad_sch (version 20250114) (generator "hlbb gen_sch.py") (generator_version "9.0")\n'
           '  (uuid "%s")\n  (paper "%s")\n  %s\n  (lib_symbols\n    %s\n  )\n  %s\n  %s\n  %s\n  %s\n  %s\n'
           '  (sheet_instances (path "/" (page "1")))\n  (embedded_fonts no)\n)\n'
           % (root_uuid, D.PAPER, title, "\n    ".join(lib_symbols), "\n  ".join(noconns),
              "\n  ".join(wires), "\n  ".join(labels), "\n  ".join(symbols), text))

    out = os.path.join(OUT_DIR, D.PROJECT + ".kicad_sch")
    open(out, "w", encoding="utf-8").write(sch)
    print("wrote", out)

    pro = os.path.join(OUT_DIR, D.PROJECT + ".kicad_pro")
    if not os.path.exists(pro):
        open(pro, "w").write('{\n  "meta": { "filename": "%s.kicad_pro", "version": 3 },\n'
                             '  "board": { "design_settings": {}, "layer_presets": [], "viewports": [] },\n'
                             '  "schematic": { "legacy_lib_dir": "", "legacy_lib_list": [] },\n'
                             '  "sheets": [ [ "%s", "Root" ] ]\n}\n' % (D.PROJECT, root_uuid))
        print("wrote", pro)


if __name__ == "__main__":
    main()
