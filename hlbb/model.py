"""Circuit model: parts, pins, nets, cables."""
from __future__ import annotations

from dataclasses import dataclass, field


class HlbbError(Exception):
    """Error in the circuit description (message in Polish, for the person building it)."""


@dataclass(frozen=True)
class Pin:
    part: "Part"
    index: int          # 0-based position in part.pins
    name: str           # display name, e.g. "D13", "GND.2", "+"

    @property
    def number(self) -> int:
        return self.index + 1

    @property
    def display(self) -> str:
        """Name as printed on the board (duplicates lose their .2 suffix)."""
        base, _, dup = self.name.rpartition(".")
        return base if dup.isdigit() and base else self.name

    @property
    def short(self) -> str:
        """Short name for tight spots: "D0/GPIO1" -> "D0", but "L/R" stays."""
        d = self.display
        return d if len(d) <= 5 else d.split("/")[0]

    @property
    def label(self) -> str:
        if self.display != self.name:
            return f"{self.part.ref}.{self.display} (nóżka {self.number})"
        return f"{self.part.ref}.{self.name}"

    def __repr__(self) -> str:
        return f"Pin({self.label})"


@dataclass(frozen=True)
class ModuleDef:
    """A dev board / module.

    pins: names in DIP counter-clockwise order (KiCad pin numbering): first
    side top->bottom as pin 1..n, second side back up.
    width: distance between the two pin rows in 0.1" pitches; None = does not
    fit a breadboard (drawn beside it).
    """
    name: str
    pins: tuple[str, ...]
    width: int | None = None
    kicad_symbol: str | None = None
    kicad_footprint: str | None = None


# Part kinds
TWO_LEG = {"resistor", "cap", "cap_e", "diode", "led", "fuse"}
# three legs in one row, consecutive columns (TO-92 transistor/sensor/regulator, trimmer)
INLINE = {"header", "to92", "pot", "led_rgb"}


class Part:
    def __init__(self, ref: str, kind: str, value: str, pin_names: list[str],
                 width: int | None = None, mdef: ModuleDef | None = None,
                 kicad_symbol: str | None = None, kicad_footprint: str | None = None,
                 kind_pl: str | None = None, bidirectional: bool = False):
        self.ref = ref
        self.kind = kind
        self.value = value
        # what the part is called in pictures and assembly steps ("tranzystor",
        # "mostek prostowniczy"); None = the default name of the kind
        self.kind_pl = kind_pl
        # a diode with no polarity (bidirectional TVS such as P6KE33CA)
        self.bidirectional = bidirectional
        self.width = width
        self.mdef = mdef
        self.kicad_symbol = kicad_symbol or (mdef.kicad_symbol if mdef else None)
        self.kicad_footprint = kicad_footprint or (mdef.kicad_footprint if mdef else None)
        names, seen = [], {}
        for n in pin_names:
            seen[n] = seen.get(n, 0) + 1
            names.append(n if seen[n] == 1 else f"{n}.{seen[n]}")
        self.pins = [Pin(self, i, n) for i, n in enumerate(names)]
        self.base_names = list(pin_names)

    def __getitem__(self, key) -> Pin:
        if isinstance(key, int):
            if 1 <= key <= len(self.pins):
                return self.pins[key - 1]
            raise HlbbError(f"{self.ref}: nie ma nóżki numer {key} (ma {len(self.pins)})")
        for p in self.pins:
            if p.name == key:
                return p
        for p in self.pins:                      # "D13" matches "D13", "SCK" matches "SCK/D5"
            base, _, dup = p.name.partition(".")
            if not dup and key in base.split("/"):
                return p
        raise HlbbError(f"{self.ref}: nie ma nóżki „{key}” "
                        f"(są: {', '.join(p.name for p in self.pins)})")

    def internal_groups(self) -> list[list[Pin]]:
        """Pins connected inside the part (same base name on a module, button pairs)."""
        groups: dict[str, list[Pin]] = {}
        if self.kind in ("module", "dip"):
            for p, base in zip(self.pins, self.base_names):
                groups.setdefault(base, []).append(p)
        elif self.kind == "button":
            groups = {"A": [self.pins[0], self.pins[1]], "B": [self.pins[2], self.pins[3]]}
        return [g for g in groups.values() if len(g) > 1]

    @property
    def is_module(self) -> bool:
        return self.kind == "module"

    def __repr__(self) -> str:
        return f"Part({self.ref} {self.value})"


@dataclass
class Net:
    name: str
    pins: list[Pin]
    color: str | None = None


@dataclass
class Cable:
    a: Pin
    b: Pin
    color: str


@dataclass
class Circuit:
    title: str
    board: object = None          # BoardType or None
    notes: str = ""
    parts: list[Part] = field(default_factory=list)
    nets: list[Net] = field(default_factory=list)
    cables: list[Cable] = field(default_factory=list)
    pcb_positions: dict = field(default_factory=dict)

    def pcb_place(self, ref: str, x_mm: float, y_mm: float, rot: int = 0):
        """Pin a part on the PCB (v2); others are packed automatically."""
        self.pcb_positions[ref] = (x_mm, y_mm, rot)

    def __post_init__(self):
        from .breadboard import Breadboard
        self.breadboard = Breadboard(self, self.board) if self.board else None

    # --- factories -------------------------------------------------------
    def _add(self, part: Part) -> Part:
        if any(p.ref == part.ref for p in self.parts):
            raise HlbbError(f"Oznaczenie {part.ref} użyte dwa razy")
        self.parts.append(part)
        return part

    def resistor(self, ref, value, **kw):
        return self._add(Part(ref, "resistor", value, ["1", "2"], **kw))

    def cap(self, ref, value, **kw):
        return self._add(Part(ref, "cap", value, ["1", "2"], **kw))

    def cap_electrolytic(self, ref, value, **kw):
        return self._add(Part(ref, "cap_e", value, ["+", "-"], **kw))

    def diode(self, ref, value, **kw):
        return self._add(Part(ref, "diode", value, ["A", "K"], **kw))

    def led(self, ref, value="LED", **kw):
        return self._add(Part(ref, "led", value, ["A", "K"], **kw))

    def fuse(self, ref, value, **kw):
        """Fuse with two legs and no polarity: polymer PTC (flat disc) or glass."""
        return self._add(Part(ref, "fuse", value, ["1", "2"], **kw))

    def transistor(self, ref, value, pins=("C", "B", "E"), **kw):
        """TO-92 transistor. pins = leg names left to right, seen from the flat face
        (datasheet order: BC547 = C, B, E; 2N7000 = S, G, D)."""
        kw.setdefault("kind_pl", "tranzystor")
        return self._add(Part(ref, "to92", value, list(pins), **kw))

    def to92(self, ref, value, pins, **kw):
        """Anything else in a TO-92 body (DS18B20, 78L05, TL431...): same shape and
        orientation rule as transistor()."""
        if len(pins) != 3:
            raise HlbbError(f"{ref}: obudowa TO-92 ma 3 nóżki")
        return self._add(Part(ref, "to92", value, list(pins), **kw))

    def led_rgb(self, ref, value="RGB", common="A", pins=None, **kw):
        """5 mm RGB LED, 4 legs in a row. common = "A" (common anode, to +) or "K" (common
        cathode, to ground). pins = leg names in order; the default is the usual layout
        (single leg = red, then the longest = common, then green, blue), measured on a
        real part."""
        if common not in ("A", "K"):
            raise HlbbError(f"{ref}: common musi być \"A\" (wspólna anoda) albo \"K\" (katoda)")
        pins = list(pins or ("R", common, "G", "B"))
        if len(pins) != 4 or common not in pins:
            raise HlbbError(f"{ref}: dioda RGB ma 4 nóżki, w tym wspólną „{common}”")
        kw.setdefault("kind_pl", "dioda LED RGB")
        part = self._add(Part(ref, "led_rgb", value, pins, **kw))
        part.common = common
        return part

    def pot(self, ref, value, **kw):
        """Potentiometer / trimmer with 3 legs in a row: 1, wiper (W), 3."""
        kw.setdefault("kind_pl", "potencjometr")
        return self._add(Part(ref, "pot", value, ["1", "W", "3"], **kw))

    def dip(self, ref, value, pins: list[str], width: int = 3, **kw):
        if len(pins) % 2:
            raise HlbbError(f"{ref}: układ DIP musi mieć parzystą liczbę nóżek")
        return self._add(Part(ref, "dip", value, list(pins), width=width, **kw))

    def header(self, ref, n: int, value=None, names: list[str] | None = None, **kw):
        names = names or [str(i + 1) for i in range(n)]
        return self._add(Part(ref, "header", value or f"goldpin 1x{n}", names, **kw))

    def button(self, ref, value="przycisk", **kw):
        return self._add(Part(ref, "button", value, ["A1", "A2", "B1", "B2"], **kw))

    def module(self, ref, mdef: ModuleDef, value=None, **kw):
        return self._add(Part(ref, "module", value or mdef.name, list(mdef.pins),
                              width=mdef.width, mdef=mdef, **kw))

    # --- connections -----------------------------------------------------
    def net(self, name: str, *pins: Pin, color: str | None = None) -> Net:
        for p in pins:
            if not isinstance(p, Pin):
                raise HlbbError(f"Sieć {name}: {p!r} to nie nóżka elementu")
        for n in self.nets:
            if n.name == name:
                n.pins.extend(pins)
                return n
        n = Net(name, list(pins), color)
        self.nets.append(n)
        return n

    def cable(self, a: Pin, b: Pin, color: str = "blue") -> Cable:
        cab = Cable(a, b, color)
        self.cables.append(cab)
        return cab

    def net_of(self, pin: Pin) -> Net | None:
        for n in self.nets:
            if pin in n.pins:
                return n
        return None
