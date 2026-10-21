# Parts reference (`kit/electronics.mjs`)

All sizes are world units. `MM` is 4 units per millimetre and `PITCH` is 2.54 mm. The board top is `z = 0`. `P` is the projection from `fitProjection`.

## Board and copper

| Function | Returns | Notes |
|---|---|---|
| `board(plan, P, { thickness, standoff, inset })` | markup | Halo, four hex standoffs, the board slab, a silkscreen border, plated mounting holes with slotted hex nuts. Defaults: 1.6 mm board, 8 mm standoffs, holes 4 mm in. |
| `trace(points, P, { flow, z })` | `{ d, svg, flow }` | A copper trace through floor points `[x, y]`. With `flow: "id"` it also returns a dotted `.el-flow` line; move its `stroke-dashoffset` to show current. Draw `svg` with the copper, `flow` after vias and silkscreen. |
| `pad(x, y, P, { r, lead })` | markup | A round pad. With `lead` (the lead radius) it adds a solder fillet, otherwise a drill hole. |
| `via(x, y, P)` | markup | A small plated hole to the other layer. |
| `pathOf(points, P)` | `d` | A polyline through 3D points. |

## Passives

| Function | Notes |
|---|---|
| `resistor({ from, to, y, bands, z, length, r, lead }, P)` | Axial, lying along x between pads at `from` and `to`. `bands` is `colourCode(ohms)`: four bands, two digits, multiplier, tolerance. Body 6.3 × 2.5 mm by default. |
| `electrolytic({ x, y, r, h, pitch }, P)` | Radial can, 5 × 7 mm by default, with a groove, a polarity stripe and a vent cross. |
| `colourCode(ohms, tolerance = "gold")` | `["4", "7", "0", "gold"]` for 47 Ω. Band colours are `.el-band[data-c]`. |

## Semiconductors

| Function | Returns | Notes |
|---|---|---|
| `led({ x, y, pitch, z, r, body }, P)` | `{ svg, glow, lensAt }` | A 5 mm LED on two legs. The lens is the lit part, wrapped in `[data-part="led"]`; set the CSS variable `--el-on` (0–1) on it. `glow` is a circle (`[data-part="glow"]`) to draw last and fade with `opacity`. Its colour is `--el-led` and `--el-led-core` in `ELEC_CSS`; override them for green, blue or white LEDs. |
| `dip({ x, y, pins, label, h }, P)` | markup | A DIP chip with pin-1 notch and dot, legs into two rows of pads 7.62 mm apart. `label` is its one engraved marking. |

## Electromechanical

| Function | Returns | Notes |
|---|---|---|
| `header({ x, y, count }, P)` | markup | Square-post pin header along x. |
| `potentiometer({ x, y, size, h, knobR, knobH }, P)` | `{ svg, pointer(turn), pins, top }` | A 9 mm board pot with a knurled knob and a 300° scale on its top. `pointer(turn)` is the index line for `turn` 0–1; rebuild it per frame. `pins` are the three pad positions, wiper in the middle. |
| `coinCell({ x, y, r, label }, P)` | `{ svg, plus, minus }` | A CR2032 in a holder; the clip over the top reaches the + pad behind it. |
| `panelMeter({ x, y, w, d, h, span, ticks, every }, P)` | `{ svg, needle(f), pins, face, pivot, R, at }` | A moving-coil meter facing +y with an arc scale. `needle(f)` gives the pointer for a deflection 0–1; draw it with `data-free="both"` right after the meter so it sorts with it. |

## Styles

`ELEC_CSS` adds `.el-trace`, `.el-flow`, `.el-pad`, `.el-hole`, `.el-band`, `.el-glow` and `.el-led`, with light-theme values. `ELEC_DEFS` holds the glow gradient (`#el-glow`) and goes once inside the SVG.

## Real numbers worth knowing

| Part | Number |
|---|---|
| Red / yellow LED | about 1.8–2.1 V, 20 mA max continuous |
| Green / blue / white LED | about 2.8–3.3 V, 20 mA max |
| CR2032 | 3.0 V, about 15 Ω internal, 220 mAh |
| AA alkaline | 1.5 V, about 0.15 Ω internal |
| 9 V battery | 9 V, about 1–2 Ω internal |
| 1/4 W resistor | 6.3 × 2.5 mm body, E12 values (10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82) |
| RC time constant | τ = R·C; 63% after τ, 99% after 5τ |
| Logic levels | 5 V CMOS high above 3.5 V; 3.3 V high above 2.0 V |
