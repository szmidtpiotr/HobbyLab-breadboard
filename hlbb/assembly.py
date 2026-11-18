"""Step-by-step assembly list (assembly.json) for montaz.html and for any app that wants
to import the build as data -- see docs/06-integracja.md."""
from __future__ import annotations

import hashlib
import json
import math
import re

from .breadboard import Hole
from .check import check
from .model import Circuit, Part, Pin
from .svg import color_pl

FORMAT, VERSION = "hlbb-assembly", 1

KIND_PL = {
    "resistor": "rezystor", "cap": "kondensator ceramiczny", "cap_e": "kondensator elektrolityczny",
    "diode": "dioda", "led": "dioda LED", "dip": "układ scalony", "header": "listwa goldpin",
    "button": "przycisk", "module": "moduł", "fuse": "bezpiecznik",
    "to92": "element w obudowie TO-92", "pot": "potencjometr", "led_rgb": "dioda LED RGB",
}


def kind_name(part: Part) -> str:
    """What the part is called in the steps: its own kind_pl, else the kind's name."""
    return part.kind_pl or KIND_PL.get(part.kind, part.kind)


BAND = ["czarny", "brązowy", "czerwony", "pomarańczowy", "żółty", "zielony", "niebieski",
        "fioletowy", "szary", "biały"]
GROUPS = [
    ("zbierz", "Przygotowanie"),
    ("moduly", "Moduły i układy scalone"),
    ("niskie", "Elementy niskie"),
    ("wysokie", "Elementy wyższe"),
    ("przewody", "Przewody na płytce"),
    ("kable", "Przewody do modułów obok płytki"),
    ("kontrola", "Kontrola"),
]
PART_GROUP = {"module": "moduly", "dip": "moduly", "resistor": "niskie", "diode": "niskie",
              "cap": "wysokie", "cap_e": "wysokie", "led": "wysokie", "button": "wysokie",
              "header": "wysokie", "fuse": "niskie", "to92": "wysokie", "pot": "wysokie",
              "led_rgb": "wysokie"}
POWER = {"5V", "+5V", "3V3", "+3V3", "VCC", "VIN", "VBUS", "VDD", "12V", "+12V"}


def resistor_ohms(value: str) -> float | None:
    v = value.replace("Ω", "").replace("ohm", "").replace(" ", "").replace(",", ".")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([RrkKmM]?)(\d*)", v)
    if not m:
        return None
    num, mult, tail = m.groups()
    if tail:                                  # 4k7 style
        if "." in num:
            return None
        num = f"{num}.{tail}"
    f = {"": 1, "R": 1, "r": 1, "k": 1e3, "K": 1e3, "m": 1e6, "M": 1e6}[mult]
    ohms = float(num) * f
    return ohms if ohms > 0 else None


def resistor_bands(value: str) -> list[str] | None:
    """4-band colour code (2 digits, multiplier, gold tolerance) in Polish."""
    ohms = resistor_ohms(value)
    if ohms is None:
        return None
    exp = math.floor(math.log10(ohms)) - 1
    digits = round(ohms / 10 ** exp)
    if digits == 100:                         # rounding pushed to 3 digits
        digits, exp = 10, exp + 1
    d1, d2 = divmod(digits, 10)
    if exp == -1:
        mult = "złoty"
    elif exp == -2:
        mult = "srebrny"
    elif 0 <= exp <= 9:
        mult = BAND[exp]
    else:
        return None
    return [BAND[d1], BAND[d2], mult, "złoty"]


def _net_names_at(res, c: Circuit, end) -> set[str]:
    if isinstance(end, Pin):
        n = c.net_of(end)
        return {n.name} if n else set()
    return {n.name for p in res.strips.get(end.strip, []) if (n := c.net_of(p))}


def _end_text(end) -> str:
    if isinstance(end, Hole):
        return end.name
    return f"pin {end.display} na {end.part.value} ({end.part.ref})"


def _part_step(part: Part, holes: list[Hole]) -> tuple[str, str, list[str]]:
    """title, text, details for placing one part."""
    h = [x.name for x in holes]
    kind = kind_name(part)
    title = f"{part.ref}: {kind}" if part.value == kind else f"{part.ref}: {kind} {part.value}"
    details = []
    if part.kind == "resistor":
        text = f"Wepnij rezystor {part.value} w {h[0]} i {h[1]}. Kierunek obojętny."
        bands = resistor_bands(part.value)
        if bands:
            details.append("Paski: " + " – ".join(bands) + " (czytaj od strony dalej od złotego).")
    elif part.kind == "cap":
        text = f"Wepnij kondensator {part.value} w {h[0]} i {h[1]}. Kierunek obojętny."
    elif part.kind == "cap_e":
        text = f"Wepnij kondensator: plus (dłuższa nóżka) w {h[0]}, minus w {h[1]}."
        details.append("Minus = nóżka od strony jasnego paska z kreskami na obudowie.")
        details.append("Odwrotnie wpięty elektrolit może się nagrzać i wybrzuszyć.")
    elif part.kind == "diode" and part.bidirectional:
        text = (f"Wepnij diodę {part.value} w {h[0]} i {h[1]}. Kierunek obojętny — "
                f"to dioda dwukierunkowa, nie ma paska katody.")
    elif part.kind == "diode":
        # text kept word for word: apps that carry checks over between versions match on it
        text = f"Wepnij diodę: anoda w {h[0]}, katoda (strona z paskiem) w {h[1]}."
    elif part.kind == "fuse":
        text = f"Wepnij bezpiecznik {part.value} w {h[0]} i {h[1]}. Kierunek obojętny."
        details.append("Bezpiecznik polimerowy (PTC) to zwykle płaski, żółty krążek na dwóch "
                       "nóżkach — łatwo go pomylić z kondensatorem, sprawdź nadruk.")
    elif part.kind == "to92":
        pins = ", ".join(f"{p.display} w {x}" for p, x in zip(part.pins, h))
        text = f"Wepnij {kind} {part.value} ({part.ref}) płaską stroną z napisem do siebie: {pins}."
        details.append("„Do siebie” = w dół obrazka, w stronę rzędu j. Nóżki od lewej to "
                       f"{', '.join(p.display for p in part.pins)}, patrząc na płaską stronę.")
        details.append("Odwrotnie wpięty nie działa albo się grzeje — sprawdź napis na obudowie.")
    elif part.kind == "led_rgb":
        name = {"R": "czerwona", "G": "zielona", "B": "niebieska"}
        com = "wspólna anoda, +" if part.common == "A" else "wspólna katoda, −"
        legs = [f"najdłuższa ({com}) w {x}" if p.display == part.common
                else f"{name.get(p.display, p.display)} w {x}" for p, x in zip(part.pins, h)]
        text = f"Wepnij diodę RGB {part.value} ({part.ref}): {', '.join(legs)}."
        if part.common == "A":
            details.append("Kolor świeci, gdy jego nóżkę ściągniesz do masy przez rezystor.")
        else:
            details.append("Kolor świeci, gdy na jego nóżkę podasz plus przez rezystor.")
        details.append("Najdłuższa nóżka jest druga od strony pojedynczej (czerwonej).")
    elif part.kind == "pot":
        text = (f"Wepnij {kind} {part.value}: skrajna nóżka 1 w {h[0]}, środkowa (suwak) "
                f"w {h[1]}, skrajna nóżka 3 w {h[2]}.")
        details.append("Zamiana skrajnych nóżek tylko odwraca kierunek kręcenia.")
    elif part.kind == "led":
        text = f"Wepnij diodę LED: dłuższa nóżka (+) w {h[0]}, krótsza (−) w {h[1]}."
        details.append("Krótsza nóżka jest też od strony ściętej krawędzi obudowy.")
    elif part.kind in ("dip", "module"):
        n = len(holes) // 2
        side = "w prawo" if holes[n - 1].col > holes[0].col else "w lewo"
        text = (f"Wepnij {part.value} ({part.ref}): nóżka 1 ({part.pins[0].display}) w {h[0]}, "
                f"pierwszy rząd biegnie {side} do {h[n - 1]}, drugi rząd w {h[n]}–{h[-1]}.")
        if part.kind == "dip":
            details.append("Wycięcie albo kropka na obudowie = strona nóżki 1.")
        else:
            details.append(f"Sprawdź napis „{part.pins[0].display}” na płytce modułu przy dziurce {h[0]}.")
        details.append("Dociśnij równo obie strony, nóżki łatwo się zaginają.")
    elif part.kind == "header":
        pins = ", ".join(f"{p.display} w {x}" for p, x in zip(part.pins, h))
        text = f"Wepnij {part.value} ({part.ref}): {pins}."
    elif part.kind == "button":
        text = (f"Wepnij przycisk okrakiem nad rowkiem: nóżki w {h[0]}, {h[2]} (góra) "
                f"i {h[1]}, {h[3]} (dół).")
        details.append("Jeśli nie wchodzi, obróć o 90° — nóżki są dalej od siebie w jedną stronę.")
    else:
        text = f"Wepnij {part.ref} w {', '.join(h)}."
    return title, text, details


def build_assembly(c: Circuit) -> dict:
    res = check(c)
    out = {"format": FORMAT, "version": VERSION, "title": c.title,
           "board": c.breadboard.type.name if c.breadboard else None,
           "notes": c.notes, "ok": res.ok, "parts": [], "steps": []}
    used = [p for p in c.parts if any(q in n.pins for n in c.nets for q in p.pins)
            or (c.breadboard and c.breadboard.placement_of(p))]
    for p in c.parts:
        if p in used or any(p is e.part for cab in c.cables for e in (cab.a, cab.b)):
            out["parts"].append({"ref": p.ref, "kind": p.kind, "kind_pl": kind_name(p),
                                 "value": p.value, "bands": resistor_bands(p.value) if p.kind == "resistor" else None})
    if not res.ok:
        out["hash"] = _hash(out)
        return out

    steps = []

    def add(group, title, text, details=(), hl=()):
        steps.append({"group": group, "title": title, "text": text,
                      "details": list(details), "hl": list(hl)})

    # 1. collect
    lines = []
    for p in out["parts"]:
        extra = f" (paski: {'–'.join(p['bands'])})" if p["bands"] else ""
        lines.append(f"{p['ref']}: {p['kind_pl']} {p['value']}{extra}")
    bb = c.breadboard
    if bb and bb.wires:
        count: dict[str, int] = {}
        for w in bb.wires:
            count[w.color] = count.get(w.color, 0) + 1
        lines.append("Przewody: " + ", ".join(f"{color_pl(k)} ×{v}" for k, v in count.items()))
    add("zbierz", "Zbierz części", "Połóż przy płytce wszystko z listy i odhacz, gdy masz komplet.",
        lines)

    if bb:
        order = {g: i for i, (g, _) in enumerate(GROUPS)}
        placed = sorted(bb.placements, key=lambda pl: (order[PART_GROUP.get(pl.part.kind, "wysokie")],
                                                       min(h.col for h in pl.holes)))
        for pl in placed:
            title, text, details = _part_step(pl.part, pl.holes)
            add(PART_GROUP.get(pl.part.kind, "wysokie"), title, text, details, [f"p-{pl.part.ref}"])

        def wire_key(item):
            i, w = item
            ends = (w.a, w.b)
            off = any(isinstance(e, Pin) and not bb.placement_of(e.part) for e in ends)
            rails = [e for e in ends if isinstance(e, Hole) and e.rail]
            nets = set().union(*(_net_names_at(res, c, e) for e in ends))
            if len(rails) == 2:
                cat = 0
            elif any(r.rail.endswith("-") for r in rails) or any(n.upper().startswith("GND") for n in nets):
                cat = 1
            elif any(r.rail.endswith("+") for r in rails) or nets & POWER:
                cat = 2
            else:
                cat = 3
            cols = [e.col for e in ends if isinstance(e, Hole)] or [99]
            return (off, cat, min(cols), i)

        for i, w in sorted(enumerate(bb.wires), key=wire_key):
            off = any(isinstance(e, Pin) and not bb.placement_of(e.part) for e in (w.a, w.b))
            a, b = (w.a, w.b) if isinstance(w.a, Hole) else (w.b, w.a)
            nets = sorted(_net_names_at(res, c, a) | _net_names_at(res, c, b))
            hl = [f"w-{i}"] + [f"p-{e.part.ref}" for e in (w.a, w.b)
                               if isinstance(e, Pin) and not bb.placement_of(e.part)]
            short_b = b.name if isinstance(b, Hole) else f"{b.part.ref}.{b.display}"
            add("kable" if off else "przewody", f"Przewód {color_pl(w.color)}: {a.name} → {short_b}",
                f"Przewód {color_pl(w.color)}: z {_end_text(a)} do {_end_text(b)}.",
                _wire_details(res, a, b, nets), hl)
    else:
        for n in c.nets:
            if len(n.pins) < 2:
                continue
            first = n.pins[0]
            for p in n.pins[1:]:
                cab = next((cb for cb in c.cables if {cb.a, cb.b} == {first, p}), None)
                how = f"kablem ({color_pl(cab.color)})" if cab else "kablem albo lutem"
                add("kable", f"Sieć {n.name}", f"Połącz {first.label} z {p.label} {how}.",
                    [], [])

    add("kontrola", "Kontrola przed zasilaniem",
        "Zanim podłączysz zasilanie, porównaj płytkę z obrazkiem i sprawdź multimetrem zwarcia.",
        ["Przejdź kolumna po kolumnie z legendą obrazka.",
         "Multimetr na ciągłość: między plusem a masą nie może piszczeć.",
         "Dopiero potem podłącz USB albo zasilacz."], [])

    for k, s in enumerate(steps, 1):
        s["id"] = f"s{k:02d}"
        s["n"] = k
    out["steps"] = steps
    out["hash"] = _hash(out)
    return out


def _hash(d: dict) -> str:
    body = {k: v for k, v in d.items() if k != "hash"}
    return hashlib.sha1(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def _wire_details(res, a, b, nets) -> list[str]:
    out = []
    for e in (a, b):
        if isinstance(e, Hole) and not e.rail:
            here = [p.label for p in res.strips.get(e.strip, [])]
            if here:
                out.append(f"{e.name} — w tej kolumnie jest {', '.join(here)}.")
    if nets:
        out.append(f"Sieć: {', '.join(nets)}.")
    return out
