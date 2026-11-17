#!/usr/bin/env python3
"""Generate <project>.kicad_pcb from design.py with KiCad's pcbnew Python module.

Generic, reusable version shipped with hlbb.
Steps: board + rules -> nets -> footprints -> automatic shelf packing for parts
without a fixed "pcb" position -> outline -> silkscreen -> save + Specctra DSN.
GND pours are added after routing (import_ses.py).
"""
import math
import os
import sys

import pcbnew
from pcbnew import VECTOR2I_MM as MM

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D  # noqa: E402

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
GAP = 4.0          # mm between packed footprints (room for tracks)
MARGIN = 3.0       # mm from parts to the board edge
TITLE_H = 4.0      # mm strip at the bottom for the silkscreen title


def mm(v):
    return pcbnew.FromMM(v)


def to_mm(v):
    return pcbnew.ToMM(v)


LABEL_PAD = {}     # footprint -> extra mm on the left for silkscreen pin labels


def bbox(fp):
    try:
        b = fp.GetBoundingBox(False, False)
    except TypeError:
        b = fp.GetBoundingBox()
    extra = LABEL_PAD.get(id(fp), 0.0)
    return (to_mm(b.GetX()) - extra, to_mm(b.GetY()),
            to_mm(b.GetWidth()) + extra, to_mm(b.GetHeight()))


def main():
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    R = D.RULES
    ds.m_TrackMinWidth = mm(R["min_track"])
    ds.m_MinClearance = mm(R["min_clearance"])
    ds.m_ViasMinSize = mm(R["min_via_dia"])
    ds.m_MinThroughDrill = mm(R["min_drill"])
    ds.m_HoleToHoleMin = mm(0.5)
    ds.m_CopperEdgeClearance = mm(R["copper_edge"])
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetTrackWidth(mm(R["track"]))
    nc.SetClearance(mm(R["clearance"]))
    nc.SetViaDiameter(mm(R["via_dia"]))
    nc.SetViaDrill(mm(R["via_drill"]))
    board.SetCopperLayerCount(2)

    nets = {}
    for name in D.NETS:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        nets[name] = n
    pin2net = D.pin_net()

    # --- footprints ---------------------------------------------------------
    fps = []
    for part in D.PARTS:
        lib, name = part["footprint"].split(":")
        fp = pcbnew.FootprintLoad(os.path.join(D.KICAD_FP_DIR, lib + ".pretty"), name)
        assert fp, part["footprint"]
        fp.SetReference(part["ref"])
        fp.SetValue(part["value"])
        fp.Value().SetVisible(False)
        fp.SetPosition(MM(0, 0))
        fp.SetOrientationDegrees(part["pcb"][2] if part.get("pcb") else 0)
        for pad in fp.Pads():
            net = pin2net.get((part["ref"], pad.GetNumber()))
            if net:
                pad.SetNet(nets[net])
        if part.get("pin_labels"):
            longest = max(len(v) for v in part["pin_labels"].values())
            LABEL_PAD[id(fp)] = longest * 0.75 + 1.5
        fps.append((part, fp))

    # --- placement: fixed ones first, the rest shelf-packed -------------------
    x0, y0 = 20.0, 20.0
    free = [(p, fp) for p, fp in fps if not p.get("pcb")]
    fixed = [(p, fp) for p, fp in fps if p.get("pcb")]
    for p, fp in fixed:
        fp.SetPosition(MM(p["pcb"][0], p["pcb"][1]))
    if free:
        area = sum((bbox(fp)[2] + GAP) * (bbox(fp)[3] + GAP) for _, fp in free)
        widest = max(bbox(fp)[2] for _, fp in free)
        row_w = max(math.sqrt(area) * 1.25, widest + GAP)
        free.sort(key=lambda pf: -bbox(pf[1])[3])
        sx = x0 + MARGIN
        sy = y0 + MARGIN
        if fixed:                              # pack below the fixed parts
            sy = max(bbox(fp)[1] + bbox(fp)[3] for _, fp in fixed) + GAP
        cx, cy, shelf = sx, sy, 0.0
        for p, fp in free:
            bx, by, bw, bh = bbox(fp)
            if cx > sx and cx + bw > sx + row_w:
                cx, cy, shelf = sx, cy + shelf + GAP, 0.0
            fp.SetPosition(MM(cx - bx, cy - by))
            cx += bw + GAP
            shelf = max(shelf, bh)
    for _, fp in fps:
        board.Add(fp)

    # --- outline ----------------------------------------------------------------
    if getattr(D, "BOARD", None):
        B = D.BOARD
        bx0, by0, bx1, by1 = B["x0"], B["y0"], B["x0"] + B["w"], B["y0"] + B["h"]
    else:
        boxes = [bbox(fp) for _, fp in fps]
        bx0 = min(b[0] for b in boxes) - MARGIN
        by0 = min(b[1] for b in boxes) - MARGIN
        bx1 = max(b[0] + b[2] for b in boxes) + MARGIN
        by1 = max(b[1] + b[3] for b in boxes) + MARGIN + TITLE_H
    r = 2.0

    def line(ax, ay, bx, by):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(MM(ax, ay)); s.SetEnd(MM(bx, by))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)

    def arc(cx, cy, sx, sy, angle):
        a = pcbnew.PCB_SHAPE(board)
        a.SetShape(pcbnew.SHAPE_T_ARC)
        a.SetCenter(MM(cx, cy)); a.SetStart(MM(sx, sy))
        a.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T), False)
        a.SetLayer(pcbnew.Edge_Cuts); a.SetWidth(mm(0.1))
        board.Add(a)

    line(bx0 + r, by0, bx1 - r, by0); line(bx1, by0 + r, bx1, by1 - r)
    line(bx1 - r, by1, bx0 + r, by1); line(bx0, by1 - r, bx0, by0 + r)
    arc(bx1 - r, by0 + r, bx1 - r, by0, 90)
    arc(bx1 - r, by1 - r, bx1, by1 - r, 90)
    arc(bx0 + r, by1 - r, bx0 + r, by1, 90)
    arc(bx0 + r, by0 + r, bx0, by0 + r, 90)

    # --- silkscreen ---------------------------------------------------------------
    def silk(text, x, y, size=0.9, right=False, angle=0):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(text)
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
        t.SetTextThickness(mm(0.15))
        t.SetTextAngleDegrees(angle)
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_RIGHT if right else pcbnew.GR_TEXT_H_ALIGN_LEFT)
        t.SetPosition(MM(x, y))
        board.Add(t)

    # pin names next to connector pads (modules on a cable, pin headers)
    for part, fp in fps:
        labels = part.get("pin_labels")
        if not labels:
            continue
        for pad in fp.Pads():
            lab = labels.get(pad.GetNumber())
            if lab:
                pos = pad.GetPosition()
                silk(lab, to_mm(pos.x) - 1.8, to_mm(pos.y) + 0.45, size=0.8, right=True)

    max_chars = int((bx1 - bx0 - 5) / 1.0)
    title = D.SILK_TITLE if len(D.SILK_TITLE) <= max_chars else D.SILK_TITLE[:max_chars - 2].rstrip() + ".."
    silk(title, bx0 + 2.5, by1 - 1.8, size=1.1)

    out = os.path.join(OUT_DIR, D.PROJECT + ".kicad_pcb")
    pcbnew.SaveBoard(out, board)
    # Custom DRC rules: one thermal spoke is enough for hand-soldered THT pads in
    # dense headers (default 2 fails as "starved_thermal" next to neighbouring pads).
    with open(os.path.join(OUT_DIR, D.PROJECT + ".kicad_dru"), "w") as f:
        f.write('(version 1)\n(rule "one spoke is enough"\n  (constraint min_resolved_spokes 1))\n')
    print("wrote", out, "board %.1f x %.1f mm" % (bx1 - bx0, by1 - by0))
    dsn = os.path.join(OUT_DIR, D.PROJECT + ".dsn")
    ok = pcbnew.ExportSpecctraDSN(board, dsn)
    print("dsn", dsn, ok)


if __name__ == "__main__":
    main()
