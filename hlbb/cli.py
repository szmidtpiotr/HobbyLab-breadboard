"""hlbb render <circuit.py> [-o OUT]  ->  breadboard.svg/png, wiring.svg/png, check.txt"""
from __future__ import annotations

import argparse
import json
import os
import runpy
import sys

from .check import check
from .model import Circuit, HlbbError
from .png import to_png


def load_circuits(path: str) -> list[Circuit]:
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    ns = runpy.run_path(path, run_name="__hlbb__")
    found = [v for v in ns.values() if isinstance(v, Circuit)]
    if not found:
        raise HlbbError(f"{path}: nie znalazłem żadnego Circuit(...)")
    return found


def render(path: str, out: str | None = None, png: bool = True) -> int:
    from .assembly import build_assembly
    from .montaz import render_montaz
    from .render_bb import render_breadboard
    from .render_wiring import render_wiring

    circuits = load_circuits(path)
    out = out or os.path.join(os.path.dirname(os.path.abspath(path)), "out")
    os.makedirs(out, exist_ok=True)
    worst = 0
    for i, c in enumerate(circuits):
        suffix = "" if len(circuits) == 1 else f"-{i + 1}"
        files = {}
        if c.breadboard is not None:
            files[f"breadboard{suffix}"] = render_breadboard(c)
        files[f"wiring{suffix}"] = render_wiring(c)
        for name, svg in files.items():
            p = os.path.join(out, name + ".svg")
            with open(p, "w") as f:
                f.write(svg)
            if png:
                to_png(p, os.path.join(out, name + ".png"))
        res = check(c)
        with open(os.path.join(out, f"check{suffix}.txt"), "w") as f:
            f.write(f"{c.title}\n{res.report()}")
        asm = build_assembly(c)
        with open(os.path.join(out, f"assembly{suffix}.json"), "w") as f:
            json.dump(asm, f, ensure_ascii=False, indent=1)
        bare = render_breadboard(c, legend=False) if c.breadboard is not None else None
        extra = ""
        if bare is not None:
            with open(os.path.join(out, f"breadboard-bare{suffix}.svg"), "w") as f:
                f.write(bare)
            extra = f"breadboard-bare{suffix}.svg, "
        with open(os.path.join(out, f"montaz{suffix}.html"), "w") as f:
            f.write(render_montaz(asm, bare, files[f"wiring{suffix}"], res.report()))
        print(f"{c.title}: {res.report().splitlines()[0]}")
        for line in res.report().splitlines()[1:]:
            print(line)
        print(f"  pliki: {', '.join(n + '.svg/.png' for n in files)}, check{suffix}.txt, "
              f"{extra}montaz{suffix}.html, assembly{suffix}.json → {out}")
        if not res.ok:
            worst = 1
    return worst


# No default on purpose: --run reaches out over SSH, so it must be your own
# KiCad 9 host (see the "Płytka PCB" chapter in docs/), never a guessed address.
KICAD_HOST = os.environ.get("HLBB_KICAD_HOST")


def kicad(path: str, out: str | None, run: bool, project: str | None) -> int:
    import subprocess
    from .kicad import export

    circuits = load_circuits(path)
    if len(circuits) != 1:
        raise HlbbError("do KiCada: w pliku ma być dokładnie jeden Circuit(...)")
    c = circuits[0]
    res = check(c)
    if not res.ok:
        print(res.report())
        print("Najpierw popraw opis — płytki PCB nie robię z układu, który nie przechodzi sprawdzenia.")
        return 1
    out = out or os.path.join(os.path.dirname(os.path.abspath(path)), "pcb")
    proj = export(c, out, project)
    print(f"design.py + generatory → {out} (projekt {proj})")
    if not run:
        print("Dalej: skopiuj ten katalog na komputer z KiCadem 9 i uruchom tam ./flow.sh "
              "(albo hlbb kicad --run, jeśli masz ustawioną zmienną HLBB_KICAD_HOST)")
        return 0
    if not KICAD_HOST:
        raise HlbbError("--run potrzebuje zmiennej środowiskowej HLBB_KICAD_HOST "
                        "(np. user@kicad-host) — komputera z zainstalowanym KiCadem 9")
    remote = f"eda/{proj}/pcb"
    sh = lambda cmd: subprocess.run(cmd, check=False).returncode  # noqa: E731
    if sh(["ssh", KICAD_HOST, f"mkdir -p ~/{remote}"]):
        return 3
    if sh(["rsync", "-a", "--exclude", "out/", "--exclude", "__pycache__/", out + "/",
           f"{KICAD_HOST}:{remote}/"]):
        return 3
    rc = sh(["ssh", KICAD_HOST, f"cd ~/{remote} && ./flow.sh"])
    sh(["rsync", "-a", "--exclude", "*.dsn", "--exclude", "*.ses", "--exclude", "*.kicad_prl",
        f"{KICAD_HOST}:{remote}/out/", os.path.join(out, "out") + "/"])
    print("flow.sh:", "OK" if rc == 0 else f"BŁĄD (kod {rc})", f"— wyniki w {out}/out")
    return 0 if rc == 0 else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="hlbb", description="Circuit description -> breadboard picture, wiring picture, connection check, KiCad bridge")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render", help="obrazki + sprawdzenie połączeń")
    r.add_argument("circuit")
    r.add_argument("-o", "--out")
    r.add_argument("--no-png", action="store_true")
    k = sub.add_parser("kicad", help="design.py + generatory KiCad (v2); --run = cały flow na Twoim komputerze z KiCadem")
    k.add_argument("circuit")
    k.add_argument("-o", "--out")
    k.add_argument("--project")
    k.add_argument("--run", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "render":
            return render(a.circuit, a.out, png=not a.no_png)
        if a.cmd == "kicad":
            return kicad(a.circuit, a.out, a.run, a.project)
    except HlbbError as e:
        print(f"BŁĄD w opisie układu: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
