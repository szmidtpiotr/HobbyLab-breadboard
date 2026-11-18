"""Breadboard picture (top view): parts, coloured jumper wires, column/row labels."""
from __future__ import annotations

import math
from collections import defaultdict

from .breadboard import ROWS, ROW_Y, Hole, rail_has_hole
from .check import check
from .model import Circuit, Pin, TWO_LEG
from .svg import Svg, color, color_pl, text_width

P = 36                      # hole pitch in px
RAIL_Y = {"T+": -3.2, "T-": -2.2, "B+": 13.2, "B-": 14.2}
BODY = {
    "resistor": ("#dcc08a", "#6b5a2e"), "cap": ("#e8a33d", "#8a5a12"),
    "cap_e": ("#2b4f9e", "#162a55"), "diode": ("#2a2a2a", "#000"), "led": ("#e23b3b", "#8a1010"),
    "fuse": ("#f2c14e", "#8a6a10"), "buzzer": ("#222222", "#000"), "mic": ("#a0a0a0", "#555"),
    "ldr": ("#e9b44c", "#8a6a10"),
}


def _off_board_parts(c: Circuit):
    bb = c.breadboard
    seen, out = set(), []
    for w in bb.wires:
        for e in (w.a, w.b):
            if isinstance(e, Pin) and not bb.placement_of(e.part) and e.part.ref not in seen:
                seen.add(e.part.ref)
                out.append(e.part)
    return out


def render_breadboard(c: Circuit, legend: bool = True) -> str:
    bb = c.breadboard
    if bb is None:
        raise ValueError("układ nie ma płytki stykowej")
    t = bb.type
    res = check(c)
    s = Svg()
    s.deferred = []

    top_extra = 4.2 if t.rails else 0.9
    X0 = 70
    Y0 = 110 + top_extra * P
    bw = (t.cols - 1) * P

    def hx(col):
        return X0 + (col - 1) * P

    def hy(y):
        return Y0 + y * P

    def hole_xy(h: Hole):
        if h.rail:
            return hx(h.col), hy(RAIL_Y[h.rail])
        return hx(h.col), hy(ROW_Y[h.row])

    # --- title -------------------------------------------------------------
    s.text(20, 36, c.title, size=24, weight="bold")
    s.text(20, 62, f"{t.name} — widok z góry. Kolumny liczone od lewej. "
                   f"Pięć dziurek w jednej kolumnie (a–e albo f–j) jest połączonych.",
           size=15, fill="#555")
    if not res.ok:
        s.text(20, 86, "UWAGA: sprawdzenie znalazło błędy — zobacz check.txt, nie buduj.",
               size=15, weight="bold", fill="#c00")

    # --- board ---------------------------------------------------------------
    ytop = (RAIL_Y["T+"] - 0.9) if t.rails else -0.9
    ybot = (RAIL_Y["B-"] + 0.9) if t.rails else 11.9
    s.rect(X0 - 40, hy(ytop), bw + 80, (ybot - ytop) * P, fill="#f4f4f0", stroke="#999", rx=10)
    s.rect(X0 - 10, hy(5.5) - 8, bw + 20, 16, fill="#e2e2dc", rx=4)

    used_strips = set(_interesting(res, bb))

    used_cols = set()
    for strip in used_strips:
        if strip.startswith("rail"):
            continue
        half, col = strip.split()
        col = int(col)
        used_cols.add(col)
        y0, y1 = (0, 4) if half == "top" else (7, 11)
        s.rect(hx(col) - 15, hy(y0) - 15, 30, (y1 - y0) * P + 30, fill="#fff3c4", stroke="#e0b400", rx=6)

    if t.rails:
        for rail, y in RAIL_Y.items():
            col_line = "#d62728" if rail[1] == "+" else "#1f63c6"
            outer = -0.5 if rail in ("T+", "B+") else 0.5
            s.line(X0 - 20, hy(y + outer), X0 + bw + 20, hy(y + outer), stroke=col_line, sw=2)
            s.text(X0 - 30, hy(y) + 5, rail[1].replace("-", "−"), size=16, anchor="middle",
                   weight="bold", fill=col_line)
            if f"rail {rail}" in used_strips:
                s.rect(X0 - 12, hy(y) - 12, bw + 24, 24, fill="none", stroke="#e0b400", sw=2, rx=6)

    for col in range(1, t.cols + 1):
        bold = "bold" if col in used_cols else "normal"
        s.text(hx(col), hy(ytop) - 10, col, size=15, anchor="middle", weight=bold)
        s.text(hx(col), hy(ybot) + 22, col, size=15, anchor="middle", weight=bold, fill="#777")
        for r in ROWS:
            s.rect(hx(col) - 5, hy(ROW_Y[r]) - 5, 10, 10, fill="#333")
        if t.rails and rail_has_hole(col):
            for y in RAIL_Y.values():
                s.rect(hx(col) - 5, hy(y) - 5, 10, 10, fill="#333")
    for r in ROWS:
        s.text(X0 - 26, hy(ROW_Y[r]) + 5, r, size=14, anchor="middle", fill="#777")
        s.text(X0 + bw + 26, hy(ROW_Y[r]) + 5, r, size=14, anchor="middle", fill="#777")

    # --- parts -----------------------------------------------------------------
    for pl in bb.placements:
        part = pl.part
        s.cur_hl = f"p-{part.ref}"
        s.add(f'<g data-hl="{s.cur_hl}">')
        if part.kind in TWO_LEG:
            _two_leg(s, part, *[hole_xy(h) for h in pl.holes])
        elif part.kind in ("dip", "module"):
            _dip(s, part, [hole_xy(h) for h in pl.holes])
        elif part.kind == "header":
            pts = [hole_xy(h) for h in pl.holes]
            s.rect(pts[0][0] - 14, pts[0][1] - 14, pts[-1][0] - pts[0][0] + 28, 28, fill="#222", rx=3)
            _label(s, (pts[0][0] + pts[-1][0]) / 2, pts[0][1] - 20, f"{part.ref} {part.value}",
                   size=14)
            if any(not p.name.isdigit() for p in part.pins):     # named pins: print them under
                for pin, (x, y) in zip(part.pins, pts):
                    _label(s, x, y + 30, pin.short, size=11, fill="#7a4b00")
        elif part.kind == "to92":
            _to92(s, part, [hole_xy(h) for h in pl.holes])
        elif part.kind == "led_rgb":
            _led_rgb(s, part, [hole_xy(h) for h in pl.holes])
        elif part.kind == "to220":
            _to220(s, part, [hole_xy(h) for h in pl.holes])
        elif part.kind == "terminal":
            _terminal(s, part, [hole_xy(h) for h in pl.holes])
        elif part.kind == "pot":
            _pot(s, part, [hole_xy(h) for h in pl.holes])
        elif part.kind == "button":
            pts = [hole_xy(h) for h in pl.holes]
            x0, y0 = pts[0][0] - 10, pts[0][1] - 10
            x1, y1 = pts[3][0] + 10, pts[3][1] + 10
            s.rect(x0, y0, x1 - x0, y1 - y0, fill="#555", stroke="#222", rx=4)
            s.circle((x0 + x1) / 2, (y0 + y1) / 2, 18, fill="#222", stroke="#888", sw=2)
            s.text((x0 + x1) / 2, y0 - 8, part.ref, size=14, anchor="middle", weight="bold")
        for h in pl.holes:
            x, y = hole_xy(h)
            s.circle(x, y, 8, stroke="#d00000", sw=3)
        s.add("</g>")
        s.cur_hl = None

    # --- off-board modules -------------------------------------------------------
    off = _off_board_parts(c)
    ox = X0 + bw + 150
    pin_xy: dict[Pin, tuple[float, float]] = {}
    oy = hy(ytop)
    max_w = 0
    for part in off:
        pins = []
        for w in bb.wires:
            for e, other in ((w.a, w.b), (w.b, w.a)):
                if isinstance(e, Pin) and e.part is part and e not in pins:
                    pins.append(e)
        pins.sort(key=lambda p: p.number)
        lw = max([text_width(p.display, 15) for p in pins] + [text_width(part.value, 15)]) + 40
        max_w = max(max_w, lw)
        hgt = 46 + 32 * len(pins)
        s.add(f'<g data-hl="p-{part.ref}">')
        s.rect(ox, oy, lw, hgt, fill="#1d2330", stroke="#111", rx=10, sw=2)
        s.text(ox + lw / 2, oy + 26, f"{part.ref}: {part.value}", size=15, anchor="middle",
               weight="bold", fill="white")
        for i, p in enumerate(pins):
            py = oy + 56 + 32 * i
            s.circle(ox, py, 6, fill="#f2c94c", stroke="#111")
            s.text(ox + 14, py + 5, p.display, size=15, fill="white")
            pin_xy[p] = (ox, py)
        s.add("</g>")
        oy += hgt + 30

    # module/IC bodies: wires should not arch over them
    bodies = []
    for pl in bb.placements:
        if pl.part.kind in ("dip", "module"):
            pts = [hole_xy(h) for h in pl.holes]
            bodies.append((min(p[0] for p in pts) - 16, min(p[1] for p in pts) - 14,
                           max(p[0] for p in pts) + 16, max(p[1] for p in pts) + 14))

    # --- wires -------------------------------------------------------------------
    for i, w in enumerate(bb.wires):
        col = color(w.color)
        a = hole_xy(w.a) if isinstance(w.a, Hole) else _pin_xy(w.a, bb, hole_xy, pin_xy)
        b = hole_xy(w.b) if isinstance(w.b, Hole) else _pin_xy(w.b, bb, hole_xy, pin_xy)
        if isinstance(w.a, Hole) and isinstance(w.b, Hole):
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            d = math.hypot(b[0] - a[0], b[1] - a[1])
            lift = min(0.3 * d, 60)
            nx, ny = (b[1] - a[1]) / (d or 1), -(b[0] - a[0]) / (d or 1)
            if ny > 0 or (ny == 0 and nx < 0):
                nx, ny = -nx, -ny
            ctrl = _best_ctrl(a, b, mx, my, nx, ny, lift, bodies)
            d_path = (f"M{a[0]:.1f},{a[1]:.1f} Q{ctrl[0]:.1f},{ctrl[1]:.1f} "
                      f"{b[0]:.1f},{b[1]:.1f}")
        else:
            c1x = a[0] + (b[0] - a[0]) * 0.45
            d_path = (f"M{a[0]:.1f},{a[1]:.1f} C{c1x:.1f},{a[1] - 40:.1f} "
                      f"{b[0] - 80:.1f},{b[1]:.1f} {b[0]:.1f},{b[1]:.1f}")
        s.add(f'<g data-hl="w-{i}">')
        s.path(d_path, stroke="#ffffff", sw=8, extra='opacity="0.8"')
        s.path(d_path, stroke=col, sw=4.5)
        for (x, y), e in ((a, w.a), (b, w.b)):
            if isinstance(e, Hole):
                s.circle(x, y, 7, fill=col, stroke="#fff", sw=1.5)
        s.add("</g>")

    _flush_labels(s)
    if not legend:
        width = max(ox + max_w + 30, X0 + bw + 80) if off else X0 + bw + 80
        return s.render(width, hy(ybot) + 40, top=hy(ytop) - 40)

    # --- legend ------------------------------------------------------------------
    ly = hy(ybot) + 70
    s.text(20, ly, "Co jest w której kolumnie:", size=17, weight="bold")
    ly += 28
    for line in _legend(c, res, bb):
        s.text(20, ly, line, size=15)
        ly += 24
    ly += 6
    for note in [l for l in c.notes.splitlines() if l.strip()]:
        s.text(20, ly, note.strip(), size=15, fill="#333")
        ly += 24
    kinds = {pl.part.kind for pl in bb.placements}
    if kinds & {"led", "cap_e", "diode"}:
        hints = []
        if "led" in kinds:
            hints.append("LED: + to dłuższa nóżka")
        if "cap_e" in kinds:
            hints.append("kondensator elektrolityczny: − to nóżka od strony paska")
        if "diode" in kinds:
            hints.append("dioda: pasek na obudowie = katoda (K)")
        s.text(20, ly + 4, "Biegunowość — " + "; ".join(hints) + ".", size=14, fill="#555")
        ly += 26
    s.text(20, ly + 4, "Zapis R1.2 = element R1, nóżka 2; U1.D13 = moduł U1, pin D13.",
           size=14, fill="#555")
    ly += 26
    s.text(20, ly + 4, "Czerwone kółka = gdzie wchodzi noga elementu. Kolorowe kropki = gdzie "
                       "wpiąć przewód. Każdy w innej dziurce tej samej kolumny.", size=14, fill="#555")
    ly += 30

    width = max(ox + max_w + 30, X0 + bw + 80, 900)
    longest = max([text_width(l, 15) + 40 for l in _legend(c, res, bb)] + [0])
    return s.render(max(width, longest), ly + 10)


def _pin_xy(p: Pin, bb, hole_xy, pin_xy):
    h = bb.hole_of(p)
    return hole_xy(h) if h else pin_xy[p]


def _label(s: Svg, x, y, text, size=15, anchor="middle", fill="#111"):
    """Part labels are drawn last (after wires) so a wire never hides them."""
    s.deferred.append((x, y, text, size, anchor, fill, getattr(s, "cur_hl", None)))


def _flush_labels(s: Svg):
    for x, y, text, size, anchor, fill, hl in s.deferred:
        if hl:
            s.add(f'<g data-hl="{hl}">')
        _draw_label(s, x, y, text, size, anchor, fill)
        if hl:
            s.add("</g>")
    s.deferred = []


def _draw_label(s: Svg, x, y, text, size, anchor, fill):
    w = text_width(text, size) * 0.95
    x0 = x - w / 2 if anchor == "middle" else x - 3
    s.rect(x0 - 3, y - size + 1, w + 6, size + 5, fill="white", rx=3, extra='opacity="0.85"')
    s.text(x, y, text, size=size, anchor=anchor, weight="bold", fill=fill)


def _seg(a, b, mx, my, half):
    """Points of a segment of length 2*half centred at (mx,my) along a->b."""
    d = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
    ux, uy = (b[0] - a[0]) / d, (b[1] - a[1]) / d
    return (mx - ux * half, my - uy * half), (mx + ux * half, my + uy * half), (ux, uy)


def _two_leg(s: Svg, part, a, b):
    s.line(a[0], a[1], b[0], b[1], stroke="#8a8a8a", sw=3)
    d = math.hypot(b[0] - a[0], b[1] - a[1])
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    fill, stroke = BODY[part.kind]

    def body(half, thick, col, edge):
        p, q, _ = _seg(a, b, mx, my, half)
        s.line(p[0], p[1], q[0], q[1], stroke=edge, sw=thick + 2, extra='stroke-linecap="round"')
        s.line(p[0], p[1], q[0], q[1], stroke=col, sw=thick, extra='stroke-linecap="round"')

    if part.kind in ("resistor", "diode"):
        half = max(min(d / 2 - 22, 30), 6)
        body(half, 20, fill, stroke)
        if part.kind == "diode" and not part.bidirectional:   # band at the cathode (pin 2 = K)
            p, q, (ux, uy) = _seg(a, b, mx + (b[0] - a[0]) / d * (half - 4),
                                  my + (b[1] - a[1]) / d * (half - 4), 3)
            s.line(p[0], p[1], q[0], q[1], stroke="#ddd", sw=20)
    elif part.kind == "cap":
        s.circle(mx, my, 13, fill=fill, stroke=stroke, sw=2)
    elif part.kind in ("buzzer", "mic"):
        rad = 17 if part.kind == "buzzer" else 13
        s.circle(mx, my, rad, fill=fill, stroke=stroke, sw=2)
        s.circle(mx, my, 4, fill="#555" if part.kind == "buzzer" else "#333")
        s.text(a[0], a[1] + 30, "+", size=18, anchor="middle", weight="bold", fill="#d00000")
        s.text(b[0], b[1] + 30, "−", size=18, anchor="middle", weight="bold", fill="#333")
    elif part.kind == "ldr":                 # disc with the meandering track
        s.circle(mx, my, 14, fill=fill, stroke=stroke, sw=2)
        s.path(f"M{mx - 8:.1f},{my - 6:.1f} h16 v4 h-16 v4 h16 v4 h-16",
               stroke="#7a3d00", sw=2)
    elif part.kind == "fuse":                # polymer PTC: a flat yellow disc
        s.circle(mx, my, 15, fill=fill, stroke=stroke, sw=2)
        s.text(mx, my + 5, "F", size=14, anchor="middle", weight="bold", fill="#5a4300")
    elif part.kind == "cap_e":
        half = max(min(d / 2 - 24, 22), 6)
        body(half, 28, fill, stroke)
        p, q, _ = _seg(a, b, mx + (b[0] - a[0]) / d * half, my + (b[1] - a[1]) / d * half, 5)
        s.line(p[0], p[1], q[0], q[1], stroke="#cfd6ea", sw=28)     # minus stripe at pin 2
        s.text(a[0], a[1] + 30, "+", size=18, anchor="middle", weight="bold", fill="#d00000")
        s.text(b[0], b[1] + 30, "−", size=18, anchor="middle", weight="bold", fill="#333")
    elif part.kind == "led":
        s.circle(mx, my, 14, fill=fill, stroke=stroke, sw=2)
        s.text(a[0], a[1] + 30, "+", size=18, anchor="middle", weight="bold", fill="#d00000")
        s.text(b[0], b[1] + 30, "−", size=18, anchor="middle", weight="bold", fill="#333")
    vertical = abs(b[0] - a[0]) < abs(b[1] - a[1])
    label = f"{part.ref} {part.value}"
    if vertical:
        _label(s, mx + 24, my + 5, label, anchor="start")
    else:
        _label(s, mx, my - 22, label)


def _pin_names_under(s: Svg, part, pts):
    for pin, (x, y) in zip(part.pins, pts):
        _label(s, x, y + 30, pin.short, size=11, fill="#7a4b00")


def _to92(s: Svg, part, pts):
    """TO-92 seen from above: a half-disc, the flat face (with the print) at the bottom
    of the picture -- legs left to right are the datasheet order seen from that face."""
    (xa, y), (xc, _) = pts[0], pts[-1]
    x0, x1 = xa - 14, xc + 14
    r, yb = (x1 - x0) / 2, y - 6
    s.path(f"M{x0:.1f},{yb:.1f} L{x1:.1f},{yb:.1f} A{r:.1f},{r:.1f} 0 0 0 {x0:.1f},{yb:.1f} Z",
           stroke="#000", sw=2, fill="#2a2a2a")
    s.line(x0 + 2, yb, x1 - 2, yb, stroke="#bbbbbb", sw=4)          # the flat face
    _label(s, (x0 + x1) / 2, yb - r - 10, f"{part.ref} {part.value}", size=14)
    _pin_names_under(s, part, pts)


def _led_rgb(s: Svg, part, pts):
    """5 mm RGB LED seen from above: a small milky dome, four legs fanning out to the
    holes; the common (longest) leg is drawn thicker."""
    xs = [p[0] for p in pts]
    y = pts[0][1]
    cx, cy, r = (xs[0] + xs[-1]) / 2, y - 34, 20
    common = part.base_names.index(part.common)
    for i, (x, _) in enumerate(pts):
        s.line(cx + (i - 1.5) * 7, cy + r - 4, x, y, stroke="#8a8a8a", sw=4 if i == common else 2.5)
    s.circle(cx, cy, r, fill="#f4f1ea", stroke="#888", sw=2)
    for i, col in enumerate(("#e02424", "#1e9e3a", "#1f5fd6")):     # the three dies
        s.circle(cx + (i - 1) * 8, cy, 4, fill=col)
    _label(s, cx, cy - r - 8, f"{part.ref} {part.value}", size=14)
    _pin_names_under(s, part, pts)


def _to220(s: Svg, part, pts):
    """TO-220 from above: the body, its printed front towards the bottom of the picture,
    the metal tab (with the hole) at the back = up the picture."""
    (xa, y), (xc, _) = pts[0], pts[-1]
    x0, x1 = xa - 18, xc + 18
    # kept low (under the next row's holes) so wires into the row behind stay visible
    s.rect(x0 + 2, y - 30, x1 - x0 - 4, 11, fill="#b8b8b8", stroke="#666", rx=2, sw=1.5)
    s.circle((x0 + x1) / 2, y - 24.5, 3, fill="#f4f4f0", stroke="#666")
    s.rect(x0, y - 20, x1 - x0, 13, fill="#2a2a2a", stroke="#000", rx=2, sw=2)
    _label(s, x1 + 4, y - 12, f"{part.ref} {part.value}", size=14, anchor="start")
    _pin_names_under(s, part, pts)


def _terminal(s: Svg, part, pts):
    y = pts[0][1]
    x0, x1 = pts[0][0] - 20, pts[-1][0] + 20
    s.rect(x0, y - 44, x1 - x0, 36, fill="#2e8b57", stroke="#1d5c39", rx=3, sw=2)
    for x, _ in pts:                          # one screw per contact
        s.circle(x, y - 26, 10, fill="#c9c9c9", stroke="#666", sw=1.5)
        s.line(x - 6, y - 26, x + 6, y - 26, stroke="#555", sw=2.5)
    _label(s, (x0 + x1) / 2, y - 52, f"{part.ref} {part.value}", size=14)
    _pin_names_under(s, part, pts)


def _pot(s: Svg, part, pts):
    (xa, y), (xc, _) = pts[0], pts[-1]
    x0, x1 = xa - 14, xc + 14
    s.rect(x0, y - 40, x1 - x0, 34, fill="#2f5fb3", stroke="#163063", rx=5, sw=2)
    cx, cy = (x0 + x1) / 2, y - 23
    s.circle(cx, cy, 11, fill="#e8e8e8", stroke="#555", sw=2)
    s.line(cx - 7, cy, cx + 7, cy, stroke="#555", sw=3)              # adjusting slot
    _label(s, cx, y - 48, f"{part.ref} {part.value}", size=14)
    _pin_names_under(s, part, pts)


def _dip(s: Svg, part, pts):
    n = len(pts) // 2
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1 = min(xs) - 16, max(xs) + 16
    y0, y1 = min(ys) + 12, max(ys) - 12
    if y1 - y0 < 20:                     # 0.3" DIP: body between the two rows
        y0, y1 = min(ys) + 12, max(ys) - 12
    fill = "#1d2330" if part.kind == "module" else "#2a2a2a"
    s.rect(x0, min(ys) - 14, x1 - x0, max(ys) - min(ys) + 28, fill=fill, stroke="#111", rx=6,
           extra='opacity="0.88"')
    # notch at the pin-1 end
    notch_x = x0 + 2 if pts[0][0] <= pts[n - 1][0] else x1 - 2
    s.circle(notch_x, (min(ys) + max(ys)) / 2, 9, fill="#f4f4f0")
    s.circle(pts[0][0], pts[0][1] + (18 if pts[0][1] == min(ys) else -18), 3.5, fill="white")
    s.text((x0 + x1) / 2, (min(ys) + max(ys)) / 2 + 6, f"{part.ref} {part.value}", size=16,
           anchor="middle", weight="bold", fill="white")
    for i, (pin, (x, y)) in enumerate(zip(part.pins, pts)):
        inward = 1 if y == min(ys) else -1
        s.text(x, y + inward * 26 + (4 if inward > 0 else 0), pin.short, size=11,
               anchor="middle", fill="#f2c94c")


def _strip_name(strip: str) -> str:
    if strip.startswith("rail"):
        r = strip.split()[1]
        side = "górna" if r[0] == "T" else "dolna"
        return f"Szyna {r[1].replace('-', '−')} ({side})"
    half, col = strip.split()
    return f"Kolumna {col} {'góra (a–e)' if half == 'top' else 'dół (f–j)'}"


def _strip_key(strip: str):
    if strip.startswith("rail"):
        return (2, strip, 0)
    half, col = strip.split()
    return (0 if half == "top" else 1, "", int(col))


def _legend(c: Circuit, res, bb) -> list[str]:
    items: dict[str, list[str]] = defaultdict(list)
    big: dict[str, int] = defaultdict(int)
    for strip, pins in res.strips.items():
        for p in pins:
            items[strip].append(p.label)
            if p.part.kind in ("dip", "module"):
                big[strip] += 1
    for w in bb.wires:
        for e, other in ((w.a, w.b), (w.b, w.a)):
            if not isinstance(e, Hole):
                continue
            if isinstance(other, Hole):
                items[e.strip].append(f"przewód {color_pl(w.color)} → {other.name}")
            else:
                h = bb.hole_of(other)
                where = f"{other.label}" + (f" ({h.name})" if h else "")
                items[e.strip].append(f"przewód {color_pl(w.color)} → {where}")
    lines = []
    keep = _interesting(res, bb)
    for strip in sorted(items, key=_strip_key):
        entries = items[strip]
        if strip not in keep:
            continue
        nets = sorted({n for p in res.strips.get(strip, []) if (n := _net_name(c, p))})
        tail = f"   → sieć {', '.join(nets)}" if nets else ""
        lines.append(f"{_strip_name(strip)}: {', '.join(entries)}{tail}")
    return lines


def _net_name(c: Circuit, p: Pin):
    n = c.net_of(p)
    if n:
        return n.name
    for grp in p.part.internal_groups():
        if p in grp:
            for q in grp:
                if (n := c.net_of(q)):
                    return n.name
    return None


def _interesting(res, bb) -> set[str]:
    """Strips worth highlighting: anything except a lone module/IC pin."""
    count: dict[str, int] = defaultdict(int)
    lone_big: dict[str, bool] = {}
    for strip, pins in res.strips.items():
        count[strip] += len(pins)
        lone_big[strip] = len(pins) == 1 and pins[0].part.kind in ("dip", "module")
    for w in bb.wires:
        for e in (w.a, w.b):
            if isinstance(e, Hole):
                count[e.strip] += 1
    return {k for k, v in count.items() if v and not (v == 1 and lone_big.get(k))}


def _best_ctrl(a, b, mx, my, nx, ny, lift, bodies):
    """Pick the arch (side and height) of a hole-to-hole wire that crosses module bodies least."""
    def hits(cx, cy):
        n = 0
        for i in range(1, 20):
            t = i / 20
            x = (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * cx + t ** 2 * b[0]
            y = (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * cy + t ** 2 * b[1]
            n += any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in bodies)
        return n
    best = None
    for sign in (1, -1):
        for k in (1.0, 0.5, 1.6, 0.2):
            cx, cy = mx + sign * nx * lift * k, my + sign * ny * lift * k
            score = (hits(cx, cy), sign == -1, abs(k - 1))
            if best is None or score < best[0]:
                best = (score, (cx, cy))
    return best[1]
