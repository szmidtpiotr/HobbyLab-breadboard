"""Connection check: what is really connected vs. what the description declares."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .breadboard import Hole
from .model import Circuit, Pin, TWO_LEG
from .svg import color_pl


class _UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


@dataclass
class CheckResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # strip id -> pins standing in it (breadboard only)
    strips: dict[str, list[Pin]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def report(self) -> str:
        lines = []
        if self.ok:
            lines.append("SPRAWDZENIE: OK — połączenia na rysunku zgadzają się z opisem układu.")
        else:
            lines.append(f"SPRAWDZENIE: {len(self.errors)} błędów — NIE buduj, popraw opis.")
        lines += [f"  BŁĄD: {e}" for e in self.errors]
        lines += [f"  uwaga: {w}" for w in self.warnings]
        return "\n".join(lines) + "\n"


def check(c: Circuit) -> CheckResult:
    res = CheckResult()
    uf = _UF()
    bb = c.breadboard
    touched: set[Pin] = set()          # pins that physically connect to something

    def node(x):
        if isinstance(x, Hole):
            return ("strip", x.strip)
        if bb and bb.hole_of(x):
            return ("strip", bb.hole_of(x).strip)
        return ("pin", x.part.ref, x.index)

    # holes used by legs and wire ends
    hole_users: dict[str, list[str]] = defaultdict(list)
    if bb:
        for pl in bb.placements:
            for pin, h in zip(pl.part.pins, pl.holes):
                hole_users[h.name].append(f"nóżka {pin.label}")
                res.strips.setdefault(h.strip, []).append(pin)
                touched.add(pin)
            if pl.part.kind in TWO_LEG and pl.holes[0].strip == pl.holes[1].strip:
                res.errors.append(
                    f"{pl.part.ref} ({pl.part.value}): obie nóżki w tym samym pasku "
                    f"({pl.holes[0].name} i {pl.holes[1].name}) — element zwarty, nic nie robi")
        for w in bb.wires:
            for e in (w.a, w.b):
                if isinstance(e, Hole):
                    hole_users[e.name].append(f"przewód {color_pl(w.color)}")
                else:
                    touched.add(e)
            uf.union(node(w.a), node(w.b))
            if isinstance(w.a, Hole) and isinstance(w.b, Hole) and w.a.strip == w.b.strip:
                res.warnings.append(f"przewód {w.a.name}–{w.b.name} łączy ten sam pasek — zbędny")
        hidden = bb.covered()
        for hole, users in hole_users.items():
            if hole in hidden:
                res.errors.append(f"dziurka {hole} jest pod modułem {hidden[hole]} — nie da się tam "
                                  f"wpiąć ({', '.join(users)}); użyj rzędu poza modułem")
            if len(users) > 1:
                res.errors.append(f"dziurka {hole} zajęta {len(users)} razy: {', '.join(users)}")
        for pl in bb.placements:
            for pin in pl.part.pins:
                uf.find(node(pin))

    if bb is None:
        # No breadboard: modules are joined by cables/soldering exactly as the
        # nets say, so the nets themselves are the physical connections.
        for n in c.nets:
            for p in n.pins[1:]:
                uf.union(node(n.pins[0]), node(p))
            touched.update(n.pins)

    for cab in c.cables:
        uf.union(node(cab.a), node(cab.b))
        touched.update((cab.a, cab.b))

    # internal connections inside parts
    internal_of: dict[Pin, list[Pin]] = {}
    for part in c.parts:
        for grp in part.internal_groups():
            for p in grp:
                internal_of[p] = grp
            for p in grp[1:]:
                uf.union(node(grp[0]), node(p))
            if any(p in touched for p in grp):
                touched.update(grp)

    def lab(p: Pin) -> str:
        h = bb.hole_of(p) if bb else None
        return f"{p.label} [{h.name}]" if h else p.label

    net_of: dict[Pin, str] = {}
    for n in c.nets:
        for p in n.pins:
            if p in net_of and net_of[p] != n.name:
                res.errors.append(f"{p.label} zadeklarowana w dwóch sieciach: {net_of[p]} i {n.name}")
            net_of[p] = n.name

    def declared_net(p: Pin):
        if p in net_of:
            return net_of[p]
        for q in internal_of.get(p, []):
            if q in net_of:
                return net_of[q]
        return None

    # every pin of every part, grouped by real connection
    groups: dict[object, list[Pin]] = defaultdict(list)
    for part in c.parts:
        for p in part.pins:
            if p in touched or p in net_of:
                groups[uf.find(node(p))].append(p)

    # 1. declared nets must be connected
    for n in c.nets:
        loose = [p for p in n.pins if p not in touched]
        for p in loose:
            res.errors.append(f"sieć {n.name}: {p.label} nie jest nigdzie wpięta ani podłączona")
        roots = defaultdict(list)
        for p in n.pins:
            if p in touched:
                roots[uf.find(node(p))].append(lab(p))
        if len(roots) > 1:
            parts = " | ".join(", ".join(v) for v in roots.values())
            res.errors.append(f"sieć {n.name} rozdzielona na {len(roots)} części, brakuje połączenia: {parts}")

    # 2. one real group must not join different nets or undeclared pins
    for root, pins in groups.items():
        nets = sorted({declared_net(p) for p in pins} - {None})
        undeclared = [p for p in pins if declared_net(p) is None]
        if len(nets) > 1:
            who = ", ".join(f"{lab(p)}({declared_net(p)})" for p in pins if declared_net(p))
            res.errors.append(f"ZWARCIE sieci {' i '.join(nets)}: {who}")
        same_part_only = (not nets and len({id(internal_of.get(p)) for p in undeclared}) == 1
                          and undeclared[0] in internal_of)
        if undeclared and (nets or len(undeclared) > 1) and not same_part_only:
            target = f"z siecią {nets[0]}" if nets else "ze sobą"
            res.errors.append(
                f"połączone {target}, a w opisie tego nie ma: {', '.join(lab(p) for p in undeclared)}")

    # 3. warnings: wire to a strip with nothing else
    if bb:
        wire_ends = defaultdict(int)
        for w in bb.wires:
            for e in (w.a, w.b):
                if isinstance(e, Hole):
                    wire_ends[e.strip] += 1
        for w in bb.wires:
            for e in (w.a, w.b):
                if isinstance(e, Hole) and not res.strips.get(e.strip) and wire_ends[e.strip] < 2:
                    res.warnings.append(f"przewód {color_pl(w.color)} do {e.name}: w tym pasku nie ma żadnej nóżki")
    return res
