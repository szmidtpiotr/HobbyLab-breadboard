#!/bin/sh
# Copy rendered hlbb output to a desktop machine and open it on its screen:
# montaz.html in the browser when present, otherwise the first PNG in the image viewer.
# Copies everything in the output dir (PNG/SVG/assembly.json/check.txt), not a hand-picked
# subset -- assembly.json in particular is meant for other tools to read later, so it must
# always travel with the pictures even though nothing opens it directly here.
#
# This script assumes an agent running on one machine (e.g. a headless dev box) and a
# human sitting at another machine with a screen, reachable over SSH with a graphical
# session already running. Set these for your own setup before using it:
#
#   HLBB_SHOW_HOST   user@host of the desktop (required, no default on purpose)
#   HLBB_SHOW_DIR    where to put files on that desktop (default: ~/Desktop/hlbb)
#   HLBB_SHOW_DISPLAY  X display + XAUTHORITY env, space-separated "VAR=val VAR=val"
#                      (default: "DISPLAY=:0"; a login-manager session may need its own
#                      XAUTHORITY path -- check `who` / `ps aux | grep Xorg` on that host)
#
# usage: pokaz.sh <dir-with-output> [name]
set -eu
SRC="$1"
NAME="${2:-$(basename "$(dirname "$(readlink -f "$SRC")")")}"
HOST="${HLBB_SHOW_HOST:?set HLBB_SHOW_HOST=user@host (the desktop machine with a screen)}"
DEST="${HLBB_SHOW_DIR:-Desktop/hlbb}/$NAME"
X="${HLBB_SHOW_DISPLAY:-DISPLAY=:0}"
ssh "$HOST" "mkdir -p ~/$DEST"
scp -q "$SRC"/* "$HOST:$DEST/" 2>/dev/null || true
if [ -f "$SRC/montaz.html" ]; then
  ssh "$HOST" "cd ~/$DEST && env $X setsid nohup xdg-open montaz.html >/dev/null 2>&1 < /dev/null &"
else
  ssh "$HOST" "cd ~/$DEST && env $X setsid nohup xdg-open $(cd "$SRC" && ls *.png | head -1) >/dev/null 2>&1 < /dev/null &"
fi
echo "$HOST:~/$DEST/"
(cd "$SRC" && ls)
