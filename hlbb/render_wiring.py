"""Module wiring picture: main board on the left, other parts on the right,
every net is its own vertical channel ("ladder"), connection table below."""
from __future__ import annotations

from .check import check
from .model import Circuit, Part, Pin
from .svg import Svg, color, color_pl, net_color, text_width

KIND_PL = {
    "resistor": "rezystor", "cap": "kondensator", "cap_e": "kondensator elektrolityczny",
    "diode": "dioda", "led": "dioda LED", "dip": "układ scalony", "header": "złącze",
    "button": "przycisk", "module": "moduł", "fuse": "bezpiecznik",
    "to92": "obudowa TO-92", "pot": "potencjometr", "led_rgb": "dioda LED RGB",
    "to220": "obudowa TO-220", "buzzer": "brzęczyk", "mic": "mikrofon", "ldr": "fotorezystor",
    "terminal": "złącze śrubowe",
}
ROW = 28
CH = 24          # channel spacing


def _main_part(c: Circuit) -> Part:
    mods = [p for p in c.parts if p.is_module]
    pool = mods or c.parts
    return max(pool, key=lambda p: len(p.pins)) if not mods else mods[0]


def render_wiring(c: Circuit) -> str:
    res = check(c)
    s = Svg()
    nets = [n for n in c.nets if len(n.pins) >= 2]
    used = {p for n in nets for p in n.pins} | {p for cab in c.cables for p in (cab.a, cab.b)}
    main = _main_part(c)
    others = [p for p in c.parts if p is not main and any(q in used for q in p.pins)]

    # net colours: explicit > cable colour > heuristic
    ncol = {}
    for i, n in enumerate(nets):
        cab = next((cb for cb in c.cables if cb.a in n.pins or cb.b in n.pins), None)
        ncol[n.name] = color(n.color) if n.color else (
            color(cab.color) if cab else net_color(n.name, None, i))

    # --- left: main part, all pins -------------------------------------------------
    top = 120
    lx = 40
    lw = max([text_width(p.display, 15) for p in main.pins] + [text_width(main.value, 17)]) + 50
    pin_pos: dict[Pin, tuple[float, float]] = {}
    lh = 50 + ROW * len(main.pins)
    s.rect(lx, top, lw, lh, fill="#1d2330", stroke="#111", rx=12, sw=2)
    s.text(lx + lw / 2, top + 30, f"{main.ref}: {main.value}", size=17, anchor="middle",
           weight="bold", fill="white")
    for i, p in enumerate(main.pins):
        y = top + 60 + ROW * i
        on = p in used
        s.text(lx + lw - 16, y + 5, p.display, size=15, anchor="end",
               fill="#f2c94c" if on else "#6d7486", weight="bold" if on else "normal")
        s.text(lx + 12, y + 5, str(p.number), size=11, fill="#6d7486")
        s.circle(lx + lw, y, 5 if on else 3, fill="#f2c94c" if on else "#6d7486")
        pin_pos[p] = (lx + lw, y)

    # --- channels -----------------------------------------------------------------
    def net_key(n):
        ys = [pin_pos[p][1] for p in n.pins if p in pin_pos]
        return (min(ys) if ys else 1e9, n.name)
    nets_sorted = sorted(nets, key=net_key)
    ch0 = lx + lw + 60
    chx = {n.name: ch0 + CH * i for i, n in enumerate(nets_sorted)}
    rx = ch0 + CH * max(len(nets_sorted) - 1, 0) + 110

    # --- right: other parts, ordered by where their nets attach on the left -------
    def part_key(part):
        ys = [net_key(n)[0] for n in nets for p in part.pins if p in n.pins]
        return (min(ys) if ys else 1e9, part.ref)
    others.sort(key=part_key)
    ry = top
    rw_max = 0
    for part in others:
        pins = [p for p in part.pins if p in used]
        title = f"{part.ref}: {part.value}"
        sub = part.kind_pl or KIND_PL.get(part.kind, part.kind)
        rw = max([text_width(p.display, 15) for p in pins] + [text_width(title, 16), text_width(sub, 13)]) + 50
        rw_max = max(rw_max, rw)
        h = 62 + ROW * len(pins)
        dark = part.kind in ("module", "dip")
        s.rect(rx, ry, rw, h, fill="#1d2330" if dark else "#f7f3e8", stroke="#111", rx=10, sw=2)
        tc = "white" if dark else "#111"
        s.text(rx + rw / 2, ry + 24, title, size=16, anchor="middle", weight="bold", fill=tc)
        s.text(rx + rw / 2, ry + 42, sub, size=13, anchor="middle", fill="#9aa" if dark else "#666")
        for i, p in enumerate(pins):
            y = ry + 66 + ROW * i
            s.circle(rx, y, 5, fill="#f2c94c", stroke="#111")
            s.text(rx + 14, y + 5, p.display, size=15, fill="#f2c94c" if dark else "#111", weight="bold")
            pin_pos[p] = (rx, y)
        ry += h + 24

    # --- draw nets ------------------------------------------------------------------
    for n in nets_sorted:
        col = ncol[n.name]
        x = chx[n.name]
        pts = [pin_pos[p] for p in n.pins if p in pin_pos]
        if len(pts) < 2:
            continue
        ys = [y for _, y in pts]
        s.line(x, min(ys), x, max(ys), stroke=col, sw=3.5)
        for (px, py), p in zip(pts, [p for p in n.pins if p in pin_pos]):
            s.line(px, py, x, py, stroke=col, sw=3.5)
            s.circle(x, py, 4.5, fill=col)
            # net name on the stub, close to the pin
            if px > x:                             # right-side pin
                tx = px - 10
                s.text(tx, py - 6, n.name, size=12, anchor="end", fill=col, weight="bold")
            else:
                s.text(px + 12, py - 6, n.name, size=12, fill=col, weight="bold")

    # --- title + table ---------------------------------------------------------------
    s.text(20, 36, f"{c.title} — połączenia", size=24, weight="bold")
    s.text(20, 62, "Każda sieć ma swój kolor i swoją pionową linię. Kropka = połączenie. "
                   "Szare piny płytki są wolne.", size=15, fill="#555")
    if not res.ok:
        s.text(20, 86, "UWAGA: sprawdzenie znalazło błędy — zobacz check.txt, nie buduj.",
               size=15, weight="bold", fill="#c00")

    ty = max(top + lh, ry) + 50
    s.text(20, ty, "Tabela połączeń:", size=17, weight="bold")
    ty += 28
    width = max(rx + rw_max + 40, 900)
    for n in nets_sorted:
        s.rect(20, ty - 13, 14, 14, fill=ncol[n.name], rx=3)
        line = f"{n.name}: " + " — ".join(p.label for p in n.pins)
        s.text(44, ty, line, size=15)
        width = max(width, 60 + text_width(line, 15))
        ty += 24
    if c.cables:
        ty += 10
        s.text(20, ty, "Kable:", size=17, weight="bold")
        ty += 26
        for cab in c.cables:
            line = f"{cab.a.label} → {cab.b.label}  ({color_pl(cab.color)})"
            s.rect(20, ty - 13, 14, 14, fill=color(cab.color), rx=3)
            s.text(44, ty, line, size=15)
            ty += 24
    for note in [l for l in c.notes.splitlines() if l.strip()]:
        s.text(20, ty + 6, note.strip(), size=15, fill="#333")
        ty += 24
    return s.render(width, ty + 20)
