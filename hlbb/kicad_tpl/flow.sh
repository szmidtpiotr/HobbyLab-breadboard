#!/usr/bin/env bash
# Full flow on your KiCad host: schematic -> ERC -> PCB -> autoroute -> DRC -> fab files -> previews
# usage: ./flow.sh [outdir]   (run from the pcb/ directory). Generic version shipped with hlbb.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HERE/out}"
P="$(cd "$HERE" && python3 -c "import design; print(design.PROJECT)")"
# Freerouting 2.5.0 CLI hangs after "Job started" (tested 2026-11-03); 2.1.0 jar works on Java 21
FR_JAR="$HOME/tools/freerouting/fr-2.1.0.jar"
mkdir -p "$OUT" "$OUT/gerber" "$OUT/preview"
cd "$HERE"

echo "== 1. schematic"
python3 gen_sch.py "$OUT"
kicad-cli sch erc --severity-error --exit-code-violations -o "$OUT/erc-errors.rpt" "$OUT/$P.kicad_sch" >/dev/null || { cat "$OUT/erc-errors.rpt"; echo "ERC FAILED"; exit 1; }
kicad-cli sch erc --severity-all -o "$OUT/erc.rpt" "$OUT/$P.kicad_sch" >/dev/null   # full report incl. warnings, for the record
tail -n 1 "$OUT/erc.rpt"
kicad-cli sch export svg --no-background-color -o "$OUT/preview" "$OUT/$P.kicad_sch" >/dev/null
kicad-cli sch export pdf -o "$OUT/preview/$P-schematic.pdf" "$OUT/$P.kicad_sch" >/dev/null
kicad-cli sch export netlist --format kicadxml -o "$OUT/$P.xml" "$OUT/$P.kicad_sch" >/dev/null

echo "== 2. board (unrouted) + DSN"
python3 gen_pcb.py "$OUT"

echo "== 3. autoroute (Freerouting)"
rm -f "$OUT/$P.ses"
timeout 600 xvfb-run -a java -jar "$FR_JAR" --gui.enabled=false -de "$OUT/$P.dsn" -do "$OUT/$P.ses" -mp 200 > "$OUT/freerouting.log" 2>&1 || true
grep -A3 "clearance_violations" "$OUT/freerouting.log" | head -3 || true
test -s "$OUT/$P.ses" || { echo "no .ses produced"; exit 1; }
python3 import_ses.py "$OUT/$P.kicad_pcb" "$OUT/$P.ses"

echo "== 4. DRC"
if kicad-cli pcb drc --severity-error --exit-code-violations -o "$OUT/drc.rpt" "$OUT/$P.kicad_pcb"; then
  tail -n 4 "$OUT/drc.rpt"
else
  cat "$OUT/drc.rpt"; echo "DRC FAILED"; exit 1
fi

echo "== 5. fabrication files (JLCPCB)"
rm -f "$OUT/gerber"/*
kicad-cli pcb export gerbers --layers F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts \
  --subtract-soldermask --no-x2 --no-netlist --use-drill-file-origin -o "$OUT/gerber/" "$OUT/$P.kicad_pcb" >/dev/null
kicad-cli pcb export drill --format excellon --drill-origin absolute --excellon-zeros-format decimal \
  --excellon-units mm --generate-map --map-format gerberx2 -o "$OUT/gerber/" "$OUT/$P.kicad_pcb" >/dev/null
kicad-cli pcb export pos --format csv --units mm --side both --smd-only -o "$OUT/$P-cpl.csv" "$OUT/$P.kicad_pcb" >/dev/null
( cd "$OUT/gerber" && rm -f "../$P-gerber-jlcpcb.zip" && zip -q "../$P-gerber-jlcpcb.zip" $(ls | grep -v drl_map) )
ls -1 "$OUT/gerber"

echo "== 6. previews"
kicad-cli pcb render --side top --quality high --background opaque --zoom 0.9 -w 1800 -h 1200 -o "$OUT/preview/$P-top.png" "$OUT/$P.kicad_pcb" >/dev/null
kicad-cli pcb render --side bottom --quality high --background opaque --zoom 0.9 -w 1800 -h 1200 -o "$OUT/preview/$P-bottom.png" "$OUT/$P.kicad_pcb" >/dev/null
kicad-cli pcb export svg --layers F.Cu,B.Cu,F.SilkS,Edge.Cuts --page-size-mode 2 -o "$OUT/preview/$P-layout.svg" "$OUT/$P.kicad_pcb" >/dev/null
# what the fab will see: render the Gerbers themselves
gerbv --export=png --dpi=300 -o "$OUT/preview/$P-gerber-top.png" \
  --background="#0b3d1e" -f "#c8a03cff" "$OUT/gerber/$P-F_Cu.gtl" -f "#ffffffff" "$OUT/gerber/$P-F_Silkscreen.gto" -f "#ffff00ff" "$OUT/gerber/$P-Edge_Cuts.gm1" -f "#000000ff" "$OUT/gerber/$P.drl" 2>/dev/null || true
gerbv --export=png --dpi=300 -o "$OUT/preview/$P-gerber-bottom.png" \
  --background="#0b3d1e" -f "#c8a03cff" "$OUT/gerber/$P-B_Cu.gbl" -f "#ffff00ff" "$OUT/gerber/$P-Edge_Cuts.gm1" -f "#000000ff" "$OUT/gerber/$P.drl" 2>/dev/null || true
ls -1 "$OUT/preview"
echo "== DONE: $OUT"
