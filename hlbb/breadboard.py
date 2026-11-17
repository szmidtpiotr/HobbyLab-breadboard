"""Breadboard geometry, hole names and placements."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .model import HlbbError, Part, Pin, TWO_LEG

ROWS = "abcdefghij"
ROW_Y = {r: (i if i < 5 else i + 2) for i, r in enumerate(ROWS)}   # pitches; e=4, f=7
Y_ROW = {y: r for r, y in ROW_Y.items()}


@dataclass(frozen=True)
class BoardType:
    key: str
    name: str
    cols: int
    rails: bool


class Board:
    MINI_170 = BoardType("MINI_170", "mała płytka stykowa 170 pól", 17, False)
    HALF_400 = BoardType("HALF_400", "płytka stykowa 400 pól", 30, True)
    FULL_830 = BoardType("FULL_830", "płytka stykowa 830 pól", 63, True)



_HOLE = re.compile(r"^([a-j])(\d+)$")
_RAIL = re.compile(r"^([TB])([+-])(\d+)$")


def rail_has_hole(col: int) -> bool:
    """Rails come in groups of 5 holes with a gap every 6th column."""
    return col % 6 != 0


@dataclass(frozen=True)
class Hole:
    name: str
    col: int
    row: str | None = None       # a..j for terminal strips
    rail: str | None = None      # "T+", "T-", "B+", "B-"

    @property
    def strip(self) -> str:
        """Id of the metal strip under this hole."""
        if self.rail:
            return f"rail {self.rail}"
        half = "top" if self.row in "abcde" else "bottom"
        return f"{half} {self.col}"


@dataclass
class Placement:
    part: Part
    holes: list[Hole]            # holes[i] belongs to part.pins[i]


@dataclass
class Wire:
    a: object                    # Hole or Pin (off-board module pin)
    b: object
    color: str


class Breadboard:
    def __init__(self, circuit, btype: BoardType):
        self.circuit = circuit
        self.type = btype
        self.placements: list[Placement] = []
        self.wires: list[Wire] = []

    # --- holes -------------------------------------------------------------
    def hole(self, name: str) -> Hole:
        m = _HOLE.match(name)
        if m:
            col = int(m.group(2))
            if not 1 <= col <= self.type.cols:
                raise HlbbError(f"Dziurka {name}: płytka ma kolumny 1–{self.type.cols}")
            return Hole(name, col, row=m.group(1))
        m = _RAIL.match(name)
        if m:
            if not self.type.rails:
                raise HlbbError(f"Dziurka {name}: {self.type.name} nie ma szyn zasilania")
            col = int(m.group(3))
            if not 1 <= col <= self.type.cols or not rail_has_hole(col):
                raise HlbbError(f"Dziurka {name}: na szynie nie ma dziurki w kolumnie {col}")
            return Hole(name, col, rail=m.group(1) + m.group(2))
        raise HlbbError(f"Nieznana dziurka „{name}” (np. a5, j12, T+3, B-7)")

    def _at(self, row: str, col: int) -> Hole:
        return self.hole(f"{row}{col}")

    # --- placement ---------------------------------------------------------
    def place(self, part: Part, *holes: str) -> Placement:
        if any(pl.part is part for pl in self.placements):
            raise HlbbError(f"{part.ref} wstawiony dwa razy")
        if part.kind in TWO_LEG:
            if len(holes) != 2:
                raise HlbbError(f"{part.ref}: podaj dwie dziurki (nóżka 1, nóżka 2)")
            hs = [self.hole(h) for h in holes]
        elif part.kind in ("dip", "module"):
            if len(holes) != 1:
                raise HlbbError(f"{part.ref}: podaj jedną dziurkę — tę pod nóżką 1")
            hs = self._dip_holes(part, self.hole(holes[0]))
        elif part.kind == "header":
            a = self.hole(holes[0])
            hs = [self._at(a.row, a.col + i) for i in range(len(part.pins))]
        elif part.kind == "button":
            a = self.hole(holes[0])
            if a.row != "e":
                raise HlbbError(f"{part.ref}: przycisk stawiamy okrakiem nad rowkiem — "
                                f"podaj dziurkę w rzędzie e (lewa górna nóżka)")
            hs = [a, self._at("f", a.col), self._at("e", a.col + 2), self._at("f", a.col + 2)]
        else:
            raise HlbbError(f"{part.ref}: nie umiem wstawić elementu typu {part.kind}")
        pl = Placement(part, hs)
        self.placements.append(pl)
        return pl

    def _dip_holes(self, part: Part, pin1: Hole) -> list[Hole]:
        if part.width is None:
            raise HlbbError(f"{part.ref} ({part.value}) nie mieści się na płytce stykowej — "
                            f"połącz go przewodami (bb.wire) albo kablami (c.cable)")
        if pin1.row is None:
            raise HlbbError(f"{part.ref}: nóżka 1 nie może stać na szynie zasilania")
        y1 = ROW_Y[pin1.row]
        y2 = y1 + part.width if y1 <= 4 else y1 - part.width
        if y2 not in Y_ROW or (y1 <= 4) == (y2 <= 4):
            raise HlbbError(
                f"{part.ref}: rzędy nóżek są {part.width / 10:.1f}\" od siebie — z nóżką 1 w "
                f"rzędzie {pin1.row} drugi rząd wypada poza płytkę albo nie przechodzi nad rowkiem")
        row2 = Y_ROW[y2]
        n = len(part.pins) // 2
        # Seen from above, pins run counter-clockwise. Pin 1 in the lower half
        # (rows f-j): notch on the left, pins go right. Pin 1 in the upper half:
        # the chip is turned around, notch on the right, pins go left.
        step = 1 if y1 > 4 else -1
        last = pin1.col + step * (n - 1)
        if not 1 <= last <= self.type.cols:
            side = "w prawo" if step > 0 else "w lewo"
            raise HlbbError(f"{part.ref}: {n} nóżek od kolumny {pin1.col} {side} wychodzi za płytkę "
                            f"(nóżka 1 w dolnej połowie = nóżki idą w prawo, w górnej = w lewo)")
        side1 = [self._at(pin1.row, pin1.col + step * i) for i in range(n)]
        side2 = [self._at(row2, last - step * i) for i in range(n)]
        return side1 + side2

    def covered(self) -> dict[str, str]:
        """Holes hidden under a module/IC body (between its two pin rows) -> part ref."""
        out = {}
        for pl in self.placements:
            if pl.part.kind not in ("dip", "module"):
                continue
            ys = sorted({ROW_Y[h.row] for h in pl.holes})
            cols = {h.col for h in pl.holes}
            for col in cols:
                for y in range(ys[0] + 1, ys[-1]):
                    if y in Y_ROW:
                        out[f"{Y_ROW[y]}{col}"] = pl.part.ref
        return out

    def wire(self, a, b, color: str = "blue") -> Wire:
        ends = []
        for e in (a, b):
            if isinstance(e, str):
                ends.append(self.hole(e))
            elif isinstance(e, Pin):
                ends.append(e)
            else:
                raise HlbbError(f"Przewód: {e!r} to ani dziurka, ani nóżka")
        w = Wire(ends[0], ends[1], color)
        self.wires.append(w)
        return w

    # --- queries -------------------------------------------------------------
    def placement_of(self, part: Part) -> Placement | None:
        for pl in self.placements:
            if pl.part is part:
                return pl
        return None

    def hole_of(self, pin: Pin) -> Hole | None:
        pl = self.placement_of(pin.part)
        return pl.holes[pin.index] if pl else None
