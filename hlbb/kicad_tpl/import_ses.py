#!/usr/bin/env python3
"""Import Freerouting's .ses result, add GND pours on both layers, fill, save.
usage: import_ses.py <board.kicad_pcb> <routed.ses>
Generic version shipped with hlbb.
"""
import sys

import pcbnew

board_path, ses = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(board_path)
ok = pcbnew.ImportSpecctraSES(board, ses)
print("ses import", ok, "tracks+vias:", len(board.GetTracks()))

gnd = board.FindNet("GND")
if gnd is not None and gnd.GetNetCode() > 0:
    e = board.GetBoardEdgesBoundingBox()
    pts = ((e.GetLeft(), e.GetTop()), (e.GetRight(), e.GetTop()),
           (e.GetRight(), e.GetBottom()), (e.GetLeft(), e.GetBottom()))
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetAssignedPriority(0)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetMinThickness(pcbnew.FromMM(0.25))
        z.SetLocalClearance(pcbnew.FromMM(0.3))
        o = z.Outline()
        o.NewOutline()
        for px, py in pts:
            o.Append(px, py)
        board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
else:
    print("no GND net - no copper pour")
pcbnew.SaveBoard(board_path, board)
print("saved", board_path)
