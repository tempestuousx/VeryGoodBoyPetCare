---
name: circuit-anatomy
description: Build crafted, interactive isometric SVG figures of real electronics (circuit boards, components, meters, LEDs, chips, batteries) that explain how a circuit or electronic idea works, with live readouts driven by true circuit math. Use this whenever someone wants an electronics illustration, a circuit explainer, a "how does this circuit work" figure, an interactive breadboard or PCB drawing, or a visual for Ohm's law, LEDs, resistors, capacitors, voltage dividers, RC timing, transistors or microcontrollers, even if they never say "isometric". Builds on the anatomy skill's kit and adds a parts library (board, traces, pads, vias, resistor with colour bands, LED with glow, electrolytic capacitor, DIP chip, pin header, potentiometer, coin cell, panel meter) and pure circuit models.
license: MIT
compatibility: Needs the anatomy skill next to it (.claude/skills/anatomy), Node.js 20.10+, and Chrome or Chromium for the checks.
---

# Circuit Anatomy

This skill is the anatomy skill for electronics. A figure is a small, real circuit on a bench: a board on standoffs, copper traces, components standing on their leads, a meter whose needle moves, an LED that glows. The reader understands the circuit because they can see the parts and watch the current change. Every number on the card comes from the same circuit model that moves the needle and lights the LED.

**Read `../anatomy/SKILL.md` first.** Everything there still applies: size the job, truth first, a real object, a long parts list, painter's order, the card, calm motion, and verifying like a critic. This file only adds what is different for electronics.

One example ships with the skill. Open it before you start:

- `examples/led-dimmer/` is a coin cell driving a red LED through a 47 Ω resistor, a 1 kΩ knob and a panel ammeter. Turning the knob changes the loop resistance; the needle swings on a damped spring, dots drift along the traces at a speed set by the current, and the LED lens and glow brighten. Build it with `node examples/led-dimmer/build.mjs` (add `--light` for the light theme).

## The one idea that matters

**The circuit is the explanation.** Don't draw a schematic with boxes and arrows. Build the real board a hobbyist would solder, and make its working visible: a needle, a glow, moving charge, a knob that turns.

| Idea | Object |
|---|---|
| Ohm's law, current limiting | A coin cell, knob, resistor and LED in one loop, with an ammeter in series |
| Voltage divider | Two resistors in a stack with a voltmeter on the middle node; a slider swaps resistor values |
| RC charging, time constants | A capacitor filling from a cell through a resistor, a voltmeter needle easing up on the true exponential |
| A transistor as a switch | A small signal on the base pin of a TO-92 turning a lamp or motor on through a big current path |
| Pull-up resistor | A push button, a resistor to the supply rail and an LED that shows the pin's logic level |
| A microcontroller blinking | A DIP chip, a crystal, decoupling caps and an LED blinking at the real clock-divided rate |

## Electronics rules

These add to the anatomy craft rules.

- **True circuit math drives everything.** Put the model in `kit/circuit.mjs` style pure functions (`seriesLed`, `divider`, `rcCharge`, `parallel`) and drive the readout, needle, glow and flow from it. Use datasheet numbers: a red LED is about 2.0 V at 20 mA, a CR2032 is 3.0 V with about 15 Ω inside, a 9 V battery has 1–2 Ω inside. Write the caption from the same numbers (the example computes its caption).
- **Real sizes.** Work in millimetres times `MM` (4 units per mm). Through-hole pitch is 2.54 mm (`PITCH`). A 1/4 W resistor body is 6.3 mm long and 2.5 mm across, a 5 mm LED is 8.6 mm tall, a board is 1.6 mm thick. Use the real size, then frame the camera to fit.
- **A closed loop you can trace.** Current needs a full path. Route every trace from pad to pad in the direction conventional current flows (+ to −), so the flow dots move the right way. When a return path would cross another trace, take it through a via to the other copper layer, as a real board does; the bottom layer is not drawn.
- **Traces never cross on one layer.** Two traces that touch are a short circuit. Route around parts or use a via.
- **Parts sit on pads.** Every lead ends in a pad with a solder fillet (`pad(..., { lead })`). An empty pad has a drill hole. Nothing floats above the board without legs.
- **Colour only where colour is real.** The figure stays monochrome like anatomy, with three exceptions that are the subject: resistor colour bands (true colour code, from `colourCode(ohms)`), the LED's own colour and glow, and copper. Wires stay in the figure's tones.
- **The LED is the lit part** in most figures: set `--el-on` (0 to 1) on its `[data-part="led"]` group and the glow's `opacity`. Brightness follows `sqrt(I / Imax)`, which matches how bright it looks.
- **Meters are springs.** A moving-coil needle follows a damped spring toward the true value (stiffness about 160, drag about 14), so it swings a little and settles. Under reduced motion it moves critically damped.
- **Moving charge.** Show current as dots drifting along the traces (`trace(points, P, { flow: "id" })`, then move `stroke-dashoffset` by `speed · current`). No current, no motion. Under reduced motion the dots stand still.
- **Polarity is visible.** Mark the + side of LEDs, cells and electrolytics with a tiny silkscreen plus or the part's own stripe, and wire them the right way round.

## Workflow

Follow the anatomy workflow (size, truth, object, parts list, world, geometry, painter's order, card, live, verify). For electronics:

1. **Truth.** Write the circuit and solve it in a pure module first. Print the range of currents and voltages the figure will show (`build.mjs` prints `1.2 to 16.4 mA`).
2. **Parts list.** Board (plate, standoffs, nuts, mounting holes, silkscreen border), copper (traces, pads, vias), the circuit's components, the instrument that shows the idea (meter, LED, display) and the control (knob, button, slider). A Figure still needs 40+ parts: count pads, legs, fillets and screws.
3. **Layout.** Put the instrument at the back so it faces the viewer, the control at the front where a hand would reach, and route traces around parts. Camera azimuth 40–45°.
4. **Painter's order.** Board, then traces, vias, silkscreen and flow dots, then components sorted by `depthOf` of their centres, then the LED glow last.
5. **Verify.** Capture both themes, phone width and a 4× close-up with `../anatomy/scripts/capture.mjs`, and run `../anatomy/scripts/lines.mjs` on both pages until it prints `line ends: 0`. Set `CHROME_PATH` if Chrome is not found (in Claude Code cloud: `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`).

## Setup

| File | Use it for |
|---|---|
| `kit/electronics.mjs` | The parts library. `board`, `trace`, `pad`, `via`, `resistor`, `electrolytic`, `led`, `dip`, `header`, `potentiometer`, `coinCell`, `panelMeter`, plus `colourCode`, `pathOf`, `MM`, `PITCH`, and the styles `ELEC_CSS` and `ELEC_DEFS`. Each builder returns SVG markup for the anatomy painter's list. `references/parts.md` lists every option. |
| `kit/circuit.mjs` | Pure circuit models: `ledVoltage`, `seriesLed`, `divider`, `rcCharge`, `parallel` and `eng` for readouts like `2.18 mA`. Inline them in live code with `fn.toString()`, as the example does. |
| `../anatomy/kit/*` | The anatomy kit itself: camera, solids, lathe, tubes, audit, WebGL. |
| `../anatomy/scripts/*` | Capture, drive, line check and print tools. |

A page needs three extras beyond a normal anatomy page: put `ELEC_DEFS` first in the SVG body (the LED glow gradient), put `<style>${ELEC_CSS}</style>` before the plate in the page body, and add the LED glow markup after every part.
