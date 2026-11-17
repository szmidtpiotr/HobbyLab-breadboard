---
name: pcb
description: Draw the user a build picture for the bench — breadboard layout with parts and coloured jumper wires, module-to-module wiring diagram, strict connection check, a step-by-step assembly page — and optionally the KiCad PCB from the same description, using the hlbb tool. Use when the user invokes /pcb, or says "draw the breadboard", "show me how to wire this up", "show the connections", "make a wiring picture", "I'm going to build this on the bench, show me how", "diagram to build from", "make a PCB from this", or whenever a circuit needs to be shown so someone can build it — even if they don't name the tool. Never hand-draw SVG for this.
---

# PCB — a build picture for the bench (hlbb)

> **This is an example skill, not a ready-made one.** It was written for one particular setup
> (a user who solders but doesn't write code, an agent host and a separate desktop with a
> screen, reached over SSH). Read it once before relying on it and adjust the parts in
> brackets — paths, hostnames, who "the user" is, where `circuit.py` lives in your own
> projects — for your own setup. The technical facts (exit codes, the pitfalls list, how
> `pokaz.sh` works) are accurate; the workflow framing around them is the part to adapt.

The user builds test circuits on the bench from these pictures, tests them with you, and
later the same description can become the PCB. They solder but may not be a programmer: the
picture has to be buildable without asking questions. The tool exists so that a picture costs
~20 lines of description, not hundreds of lines of hand-written SVG.

Tool: `hlbb` (install it so it's in `PATH`; see the repo's README). `<hlbb-repo>` below means
wherever you cloned/installed it — path and remote differ per setup.

## Steps

1. **Know the circuit.** Parts, values, which pin goes where. If parts aren't decided yet
   (e.g. you're matching against a personal parts inventory, a BOM, or a shop), settle that
   first — the picture documents a decision, it doesn't make one.

2. **Read the format, nothing more.** `<hlbb-repo>/docs/opis-ukladu.md` (one page) plus the
   single closest example from `<hlbb-repo>/examples/`:
   - `nano_leds_button.py` — Nano on a 400 board, LEDs, button, rails, many wires
   - `rc_filter.py` — small 170 board, module (UNO) beside the board
   - `xiao_ring_mic.py` — no breadboard, modules joined by cables
   Do not read the hlbb source; the reference is enough and keeps this cheap.

3. **Write the description** as `circuit.py`, wherever you keep per-project files (a docs
   folder next to the firmware, a scratch directory for a one-off question — your call). Plan
   columns before writing: modules first, then each part group in its own columns, wires last.
   Use colours by meaning (red = plus, black = ground, others = signals) and LED refs `LED1…`
   so they don't clash with pin names like D2.

4. **Render and check:**
   ```bash
   hlbb render <dir>/circuit.py -o <dir>/breadboard
   ```
   - exit 2 = mistake in the description itself (bad hole/pin name) — message on stderr.
   - exit 1 = the picture does not match the nets. Messages name the hole of every pin
     (`U1.D2 [h5]`), so fix the description and render again.
   - Only exit 0 may be shown to the user. A wrong picture costs them a burnt part or an
     evening.

5. **Look at the picture yourself** (`Read` on `breadboard.png`, `wiring.png`): labels
   readable, no wire hiding a part label, polarity marks visible. Fix the layout if it's
   cramped.

6. **Show it on their screen** if your agent and the user aren't looking at the same display:
   ```bash
   HLBB_SHOW_HOST=user@desktop-host ~/.claude/skills/pcb/scripts/pokaz.sh <dir>/breadboard <name>
   ```
   (set `HLBB_SHOW_HOST` once in your shell profile instead of per call). Copies the output
   and opens `montaz.html`: a step-by-step assembly page (one action per step, the part
   described, the current part pulsing on the board, zoomable, Space = done, progress kept in
   the browser). It's what they build from; the PNGs are for a quick look. If your agent and
   the user share a filesystem and screen already, just tell them the path — skip this step.

7. **Save the files** wherever your own project convention puts generated artefacts (next to
   the firmware, committed to the project's repo, whatever you already do for this project).
   Don't leave one-off scratch circuits lying around outside your normal working area.

8. **PCB only when asked** ("make a PCB", "export to KiCad", "get this fabbed"):
   ```bash
   hlbb kicad <dir>/circuit.py -o <dir>/pcb --run
   ```
   Needs `HLBB_KICAD_HOST` set to your own KiCad 9 + Freerouting host (see the repo's "Płytka
   PCB" chapter) — `hlbb` refuses `--run` without it rather than guessing a host. Runs schematic
   → ERC → board → Freerouting → DRC → Gerbers there. Placement is automatic and basic; pin
   parts with `c.pcb_place(...)` for a real board. Never place an order yourself — that's
   always a human decision.

## Pitfalls worth knowing

- A module covers the holes between its pin rows; a WeMos D1 mini never fits one breadboard
  with both rows reachable — put it beside the board (`bb.wire("a5", d1["D4"], ...)`).
- Top and bottom rails are separate; bridge them with a wire if both are used.
- On a 400/830 board every 6th rail column has no hole (`T+6` is rejected).
- The XIAO ESP32-S3, Arduino UNO and ESP32-S3 DevKitC have no breadboard footprint in hlbb
  (their pin spacing wasn't verified) → always beside the board.
- If hlbb lacks a part you need (a sensor like DHT11, a potentiometer, a transistor in TO-92,
  …), use `c.header("U2", 3, value="DHT11", names=["VCC", "DATA", "GND"])` — the picture then
  shows the real name and the pin names under each leg. Say so in the reply: it's drawn as a
  generic pin block, not the part's real shape.
- Rails `T…` are above row a, `B…` below row j: put parts powered from a rail in that half.
  A leg may go straight into a rail (`bb.place(r, "a15", "T+15")`), which saves a wire.

## Reply to the user

First line: what was drawn and that the check passed. Then where the files are (give a full
path, and the host if it's not the machine they're looking at) and what to do next — usually
"wire it up following the legend under the picture, column by column."
