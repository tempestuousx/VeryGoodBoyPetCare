// Electronics parts for anatomy figures. Every builder takes world units
// (4 units = 1 mm by default, see MM) and returns SVG markup strings built
// with the anatomy kit, so they drop into the same painter's list.
import * as k from "../../anatomy/kit/iso-kit.mjs";
import * as G from "../../anatomy/kit/lathe.mjs";

export const MM = 4;
export const PITCH = 2.54 * MM;

const S = (paths, style) => k.solidSvg(paths, style);
const L = (d, style) => k.lineSvg(d, style);
const D = (points, style) => k.dotsSvg(points, style);
const UP = (x, y, z) => G.frameOf([x, y, z], [0, 0, 1], [1, 0, 0], [0, 1, 0]);

// A polyline through world points, as one path.
export const pathOf = (points, P) => "M" + points.map((p) => k.iso(p, P).map((v) => v.toFixed(1)).join(" ")).join("L");

// Extra styles for copper, solder, resistor bands and LED light. Append to
// the page CSS once: pageHtml({ ..., body: `<style>${ELEC_CSS}</style>` + body }).
export const ELEC_CSS = `
.iso{--el-copper:#7a6a55;--el-mask:#2c2c2c;--el-led:#ff5a4f;--el-led-core:#ffd2c8}
.iso[data-theme="light"]{--el-copper:#b39b78;--el-mask:#c9c9c4;--el-led:#e5342b;--el-led-core:#ff9d8f}
.el-trace{fill:none;stroke:var(--el-copper);stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round;opacity:.55}
.el-flow{fill:none;stroke:var(--anatomy-lit);stroke-width:1.1;stroke-linecap:round;stroke-dasharray:.01 7}
.el-pad{fill:var(--el-copper);stroke:var(--anatomy-mid);stroke-width:.45}
.el-hole{fill:var(--anatomy-halo)}
.el-band{fill:none;stroke-width:1.6;stroke-linecap:butt}
.el-band[data-c="0"]{stroke:#1a1a1a}.el-band[data-c="1"]{stroke:#7b4a2a}.el-band[data-c="2"]{stroke:#d23b2f}
.el-band[data-c="3"]{stroke:#ec7a22}.el-band[data-c="4"]{stroke:#e7c626}.el-band[data-c="5"]{stroke:#3c9a4a}
.el-band[data-c="6"]{stroke:#3d63c9}.el-band[data-c="7"]{stroke:#8a4fc4}.el-band[data-c="8"]{stroke:#8a8a8a}
.el-band[data-c="9"]{stroke:#efefef}.el-band[data-c="gold"]{stroke:#c8a24a}.el-band[data-c="silver"]{stroke:#b8b8b8}
.iso:not([data-theme="light"]) .el-band[data-c="0"]{stroke:#000}
.el-glow{fill:url(#el-glow);pointer-events:none;mix-blend-mode:screen}
.iso[data-theme="light"] .el-glow{mix-blend-mode:normal}
.el-led{--el-on:0}
.el-led .iso-solid[data-lit]>.iso-top{fill:color-mix(in srgb,var(--el-led) calc(25% + var(--el-on) * 70%),var(--anatomy-lit-top));stroke:color-mix(in srgb,var(--el-led) calc(25% + var(--el-on) * 70%),var(--anatomy-lit-top))}
.el-led .iso-solid[data-lit]>.iso-shade{fill:color-mix(in srgb,var(--el-led) calc(18% + var(--el-on) * 60%),var(--anatomy-lit-shade));stroke:color-mix(in srgb,var(--el-led) calc(18% + var(--el-on) * 60%),var(--anatomy-lit-shade))}
`;

// The radial gradient the LED glow uses. Put it once inside the <svg> body.
export const ELEC_DEFS = `<defs><radialGradient id="el-glow"><stop offset="0" stop-color="var(--el-led-core)"/><stop offset=".35" stop-color="var(--el-led)" stop-opacity=".7"/><stop offset="1" stop-color="var(--el-led)" stop-opacity="0"/></radialGradient></defs>`;

// ---- Colour code -----------------------------------------------------------

// The 4-band code for a resistance: two digits, a multiplier, a tolerance.
export function colourCode(ohms, tolerance = "gold") {
  const exp = Math.floor(Math.log10(ohms)) - 1;
  const digits = Math.round(ohms / 10 ** exp);
  return [Math.floor(digits / 10), digits % 10, exp, tolerance].map(String);
}

// ---- Board -----------------------------------------------------------------

// A circuit board on four standoffs: halo, standoffs with nuts, the board with
// its edge, a silkscreen keep-out line and plated mounting holes.
export function board(plan, P, { thickness = 1.6 * MM, standoff = 8 * MM, inset = 4 * MM } = {}) {
  const z0 = -thickness;
  const out = [`<path class="iso-halo" d="${k.haloOf(plan, z0 - standoff, standoff, P)}"/>`];
  const holes = k.corners(plan, inset);
  const byDepth = [...holes].sort((a, b) => k.depthOf([...a, 0], P) - k.depthOf([...b, 0], P));
  for (const [x, y] of byDepth) {
    out.push(S(k.cylinder(x, y, 1.6 * MM, z0 - standoff, 0.8 * MM, P, 6), { tone: "lo" }));
    out.push(S(k.cylinder(x, y, 1.1 * MM, z0 - standoff + 0.8 * MM, standoff - 0.8 * MM, P, 6), { tone: "mid" }));
  }
  out.push(S(k.slabOf(plan, z0, thickness, P, 6, 0.6), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(plan, 2 * MM), 0, P, 6), { tone: "faint" }));
  for (const [x, y] of holes) {
    out.push(`<path class="el-pad" d="${k.onTop(k.circleRing(x, y, 2.2 * MM, 28), 0, P, true)}"/>`);
    out.push(`<path class="el-hole" d="${k.onTop(k.circleRing(x, y, 1.3 * MM, 24), 0, P, true)}"/>`);
    out.push(S(k.cylinder(x, y, 2 * MM, 0, 0.6 * MM, P, 6), { tone: "mid" }));
    out.push(L(k.lineOnTop([x - 2 * MM, y], [x + 2 * MM, y], 0.6 * MM, P), { tone: "lo" }));
  }
  return out.join("");
}

// A copper trace along floor points on the board top. Returns the trace and,
// when flow is set, a dotted line on top that live code moves with
// stroke-dashoffset to show charge drifting along it.
export function trace(points, P, { flow = null, z = 0.05 } = {}) {
  const d = pathOf(points.map(([x, y]) => [x, y, z]), P);
  const flowLine = flow ? `<path class="el-flow" data-flow-part="${flow}" d="${d}"/>` : "";
  return { d, svg: `<path class="el-trace" d="${d}"/>`, flow: flowLine };
}

// A round through-hole pad with its drill, and a solder fillet when a lead
// sits in it.
export function pad(x, y, P, { r = 0.9 * MM, lead = 0 } = {}) {
  const out = [`<path class="el-pad" d="${k.onTop(k.circleRing(x, y, r, 24), 0, P, true)}"/>`];
  if (lead) out.push(S(k.cylinder(x, y, lead * 1.8, 0, 0.5 * MM, P, 18), { tone: "mid", crease: "none" }));
  else out.push(`<path class="el-hole" d="${k.onTop(k.circleRing(x, y, r * 0.45, 16), 0, P, true)}"/>`);
  return out.join("");
}

// A via: a small plated hole that takes a trace to the other copper layer.
export function via(x, y, P) {
  return `<path class="el-pad" d="${k.onTop(k.circleRing(x, y, 0.6 * MM, 20), 0, P, true)}"/>` + D([k.iso([x, y, 0], P)], { size: 0.55, tone: "hi" });
}

// A vertical leg from the board up to z, for a through-hole lead.
const leg = (x, y, z, r, P, tone = "hi") => S(k.cylinder(x, y, r, 0, z, P, 10), { tone, crease: "none" });

// ---- Passives --------------------------------------------------------------

// An axial resistor lying along x, standing off the board on its bent leads.
// `from` and `to` are the two pad x positions at row y; `bands` is colourCode().
export function resistor({ from, to, y, bands, z = 2.6 * MM, length = 6.3 * MM, r = 1.25 * MM, lead = 0.3 * MM }, P) {
  const mid = (from + to) / 2;
  const F = G.frameAlong([from, y, z], [1, 0, 0]);
  const s0 = mid - length / 2 - from;
  const s1 = mid + length / 2 - from;
  const out = [pad(from, y, P, { lead }), pad(to, y, P, { lead })];
  out.push(leg(from, y, z, lead, P), leg(to, y, z, lead, P));
  out.push(S(G.disc(0, to - from, lead, F, P), { tone: "hi", crease: "none" }));
  const bulb = r * 1.12;
  const profile = [
    [s0, 0.6 * r], [s0 + 0.15 * MM, r * 0.95, 1], [s0 + 0.6 * MM, bulb, 1], [s0 + 1.4 * MM, bulb, 1],
    [s0 + 1.9 * MM, r, 1], [s1 - 1.9 * MM, r, 1], [s1 - 1.4 * MM, bulb, 1], [s1 - 0.6 * MM, bulb, 1],
    [s1 - 0.15 * MM, r * 0.95, 1], [s1, 0.6 * r],
  ];
  const at = [s0 + 0.9 * MM, s0 + 1.7 * MM, s0 + 2.5 * MM, s1 - 1.0 * MM];
  const rings = bands.map((c, i) => `<path class="el-band" data-c="${c}" d="${G.arcOf(F, at[i], (i === 0 || i === 3 ? bulb : r) + 0.05, P)}"/>`).join("");
  out.push(S(G.solidOf(profile, F, P), { tone: "hi", crease: "none", inner: rings }));
  return out.join("");
}

// A radial electrolytic capacitor standing on the board: sleeve, top vent
// cross, polarity stripe, legs into two pads `pitch` apart along x.
export function electrolytic({ x, y, r = 2.5 * MM, h = 7 * MM, pitch = 2 * MM }, P) {
  const F = UP(x, y, 0.4 * MM);
  const out = [pad(x - pitch / 2, y, P, { lead: 0.25 * MM }), pad(x + pitch / 2, y, P, { lead: 0.25 * MM })];
  const profile = [[0, r * 0.92], [0.4 * MM, r, 1], [1.2 * MM, r * 0.93, 1], [1.8 * MM, r, 1], [h - 0.5 * MM, r, 1], [h, r * 0.9]];
  const stripe = G.ribsOf(F, 1.8 * MM, h - 0.5 * MM, r, 1, P, { phase: Math.PI * 0.2, seams: false });
  const seams = G.arcOf(F, 1.8 * MM, r, P) + G.arcOf(F, h - 0.5 * MM, r, P);
  out.push(S(G.solidOf(profile, F, P), { tone: "mid", crease: "none", inner: L(G.arcOf(F, 1.2 * MM, r * 0.93, P), { tone: "lo" }) + L(seams, { tone: "faint" }) + L(stripe, { tone: "hi" }) }));
  const top = 0.4 * MM + h;
  const v = r * 0.75;
  out.push(L(k.lineOnTop([x - v, y], [x + v, y], top, P) + k.lineOnTop([x, y - v], [x, y + v], top, P), { tone: "lo" }));
  out.push(L(k.ring(x, y, r * 0.75, top, P, 32), { tone: "faint" }));
  return out.join("");
}

// ---- Semiconductors --------------------------------------------------------

// A 5 mm LED: flange with its flat on the cathode side, body and dome, two
// legs. Returns { svg, glow } where glow is a circle live code fades with
// opacity (0 to 1) as current flows. The lens is the lit part: set the
// --el-on custom property (0 to 1) on [data-part="led"] to tint it.
export function led({ x, y, pitch = PITCH, z = 3 * MM, r = 2.5 * MM, body = 5.8 * MM }, P) {
  const lead = 0.25 * MM;
  const out = [pad(x - pitch / 2, y, P, { lead }), pad(x + pitch / 2, y, P, { lead })];
  out.push(leg(x - pitch / 2, y, z, lead, P), leg(x + pitch / 2, y, z, lead, P));
  const F = UP(x, y, z);
  const dome = [];
  for (let i = 1; i <= 10; i++) {
    const t = (i / 10) * (Math.PI / 2);
    dome.push([body + r * Math.sin(t), r * Math.cos(t), 1]);
  }
  const flange = 1.0 * MM;
  out.push(S(G.disc(0, flange, r + 0.4 * MM, F, P), { tone: "mid" }));
  out.push(`<g class="el-led" data-part="led">` + S(G.solidOf([[flange, r], [body, r, 1], ...dome], F, P), { tone: "hi", lit: true, crease: "none" }) + `</g>`);
  const top = k.iso([x, y, z + body + r * 0.4], P);
  const glowR = r * 6 * G.scaleOf(P);
  const glow = `<circle class="el-glow" data-part="glow" cx="${top[0].toFixed(1)}" cy="${top[1].toFixed(1)}" r="${glowR.toFixed(1)}" opacity="0"/>`;
  return { svg: out.join(""), glow, lensAt: top };
}

// A DIP chip: black body with pin-1 notch and dot, gull legs down each long
// side into pads. `pins` is the total count (even). Its one engraved label
// is optional.
export function dip({ x, y, pins = 8, label = "", h = 3.3 * MM }, P) {
  const per = pins / 2;
  const w = per * PITCH;
  const d = 6.4 * MM;
  const plan = { x: x - w / 2, y: y - d / 2, w, d, r: 0.4 * MM };
  const out = [];
  const rows = [y - 3.81 * MM, y + 3.81 * MM];
  for (const py of rows) for (let i = 0; i < per; i++) out.push(pad(x - w / 2 + PITCH * (i + 0.5), py, P, { lead: 0.25 * MM }));
  for (const py of rows) {
    const toward = py < y ? -1 : 1;
    for (let i = 0; i < per; i++) {
      const px = x - w / 2 + PITCH * (i + 0.5);
      const shoulder = { x: px - 0.75 * MM, y: Math.min(py, y + toward * d / 2), w: 1.5 * MM, d: Math.abs(py - (y + toward * d / 2)), r: 0.1 * MM };
      out.push(S(k.slabOf({ x: px - 0.25 * MM, y: py - 0.25 * MM, w: 0.5 * MM, d: 0.5 * MM, r: 0.1 * MM }, 0, 1.2 * MM, P, 2), { tone: "hi", crease: "none" }));
      out.push(S(k.slabOf(shoulder, 1.2 * MM, 0.3 * MM, P, 2), { tone: "hi", crease: "none" }));
    }
  }
  out.push(S(k.slabOf(plan, 0.8 * MM, h - 0.8 * MM, P, 2, 0.4), { tone: "lo", crease: "faint" }));
  const top = h;
  const notch = Array.from({ length: 9 }, (_, i) => {
    const t = -Math.PI / 2 + (i / 8) * Math.PI;
    return [plan.x + Math.cos(t) * 0.9 * MM, y + Math.sin(t) * 0.9 * MM];
  });
  out.push(L(k.onTop(notch, top, P), { tone: "faint" }));
  out.push(D([k.iso([plan.x + 1.4 * MM, plan.y + d - 1.4 * MM, top], P)], { size: 0.7, tone: "mid" }));
  if (label) out.push(k.faceTextSvg(k.topMatrix([x, y + 0.5 * MM], top, P, "x"), label, { size: 2.2, tone: "lo", anchor: "middle" }));
  return out.join("");
}

// A row of square-post header pins in a plastic strip, along x.
export function header({ x, y, count = 2 }, P) {
  const w = count * PITCH;
  const out = [];
  for (let i = 0; i < count; i++) out.push(pad(x + PITCH * (i + 0.5), y, P, { lead: 0.32 * MM }));
  out.push(S(k.slabOf({ x, y: y - PITCH / 2, w, d: PITCH, r: 0.3 * MM }, 0, 2.5 * MM, P, 2, 0.3), { tone: "lo" }));
  for (let i = 0; i < count; i++) {
    const px = x + PITCH * (i + 0.5);
    out.push(S(k.slabOf({ x: px - 0.32 * MM, y: y - 0.32 * MM, w: 0.64 * MM, d: 0.64 * MM, r: 0.08 * MM }, 2.5 * MM, 6 * MM, P, 2), { tone: "hi", crease: "none" }));
  }
  return out.join("");
}

// ---- Electromechanical -----------------------------------------------------

// A 9 mm board-mount potentiometer: square body, bushing, shaft and a knurled
// knob. Three legs come out of the front (+y) face into pads. Returns
// { svg, pointer(turn) } where pointer gives the knob index line for a turn
// fraction from 0 to 1 over the 300° sweep.
export function potentiometer({ x, y, size = 10 * MM, h = 7 * MM, knobR = 3.2 * MM, knobH = 5 * MM }, P) {
  const plan = { x: x - size / 2, y: y - size / 2, w: size, d: size, r: 0.6 * MM };
  const pinsY = y + size / 2 + 1.6 * MM;
  const pins = [-PITCH * 2, 0, PITCH * 2].map((dx) => [x + dx, pinsY]);
  const out = pins.map(([px, py]) => pad(px, py, P, { lead: 0.3 * MM }));
  for (const [px, py] of pins) {
    out.push(S(k.slabOf({ x: px - 0.4 * MM, y: y + size / 2 - 0.2 * MM, w: 0.8 * MM, d: py - y - size / 2 + 0.6 * MM, r: 0.1 * MM }, 0.8 * MM, 0.4 * MM, P, 2), { tone: "hi", crease: "none" }));
    out.push(S(k.slabOf({ x: px - 0.4 * MM, y: py - 0.2 * MM, w: 0.8 * MM, d: 0.4 * MM, r: 0.1 * MM }, 0, 1.2 * MM, P, 2), { tone: "hi", crease: "none" }));
  }
  out.push(S(k.slabOf(plan, 0.6 * MM, h - 0.6 * MM, P, 3, 0.5), { tone: "mid" }));
  out.push(L(k.sideSeam(plan, 2.4 * MM, P, 3), { tone: "faint" }));
  for (const [dx, dy] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
    out.push(D([k.iso([x + dx * (size / 2 - 1.2 * MM), y + dy * (size / 2 - 1.2 * MM), h], P)], { size: 0.45, tone: "lo" }));
  }
  const bushing = 2.6 * MM;
  out.push(S(k.cylinder(x, y, bushing, h, 1.5 * MM, P, 36, 0.4), { tone: "mid" }));
  out.push(L(k.knurl(x, y, bushing, h + 0.2 * MM, h + 1.3 * MM, 20, P, 0.2), { tone: "faint" }));
  out.push(S(k.cylinder(x, y, 2.3 * MM, h + 1.5 * MM, 1.5 * MM, P, 6), { tone: "mid", crease: "lo" }));
  const z0 = h + 3 * MM;
  out.push(S(k.cylinder(x, y, knobR, z0, knobH, P, 48, 0.5), { tone: "hi", crease: "lo" }));
  out.push(L(k.knurl(x, y, knobR, z0 + 0.6 * MM, z0 + knobH - 1 * MM, 40, P, 0.3), { tone: "lo" }));
  out.push(L(k.sideArc(x, y, knobR, z0 + 0.6 * MM, P, 32) + k.sideArc(x, y, knobR, z0 + knobH - 1 * MM, P, 32), { tone: "faint" }));
  const top = z0 + knobH;
  const ticks = k.radialTicks(x, y, knobR + 1.6 * MM, 10, 5, h, [0.5 * MM, 0.9 * MM], P, -Math.PI * 5 / 6, Math.PI * 5 / 3);
  out.push(L(ticks.minor, { tone: "lo" }), L(ticks.major, { tone: "mid" }));
  const pointer = (turn) => {
    const a = -Math.PI * 5 / 6 + turn * Math.PI * 5 / 3;
    return k.lineOnTop([x + Math.sin(a) * 1.2 * MM, y - Math.cos(a) * 1.2 * MM], [x + Math.sin(a) * (knobR - 0.8 * MM), y - Math.cos(a) * (knobR - 0.8 * MM)], top, P);
  };
  return { svg: out.join(""), pointer, pins, top };
}

// A CR2032 coin cell in a board holder: the holder ring, the cell with its
// engraving, and the spring clip that reaches over it to the + pad behind.
// Returns { svg, plus, minus } pad positions.
export function coinCell({ x, y, r = 10 * MM, label = "CR2032" }, P) {
  const plus = [x, y - r - 3 * MM];
  const minus = [x, y + r + 3 * MM];
  const out = [pad(...plus, P, { lead: 0.4 * MM }), pad(...minus, P, { lead: 0.4 * MM })];
  out.push(S(k.slabOf({ x: minus[0] - 1.6 * MM, y: y + r - 0.4 * MM, w: 3.2 * MM, d: minus[1] - y - r + 1.2 * MM, r: 0.3 * MM }, 0, 0.6 * MM, P, 2), { tone: "hi", crease: "none" }));
  out.push(S(k.cylinder(x, y, r + 1.4 * MM, 0, 1.6 * MM, P, 64, 0.4), { tone: "lo" }));
  out.push(L(k.ring(x, y, r + 0.4 * MM, 1.6 * MM, P, 64), { tone: "faint" }));
  const cellZ = 1.6 * MM;
  const cellH = 3.2 * MM;
  out.push(S(k.cylinder(x, y, r, cellZ, cellH, P, 72, 0.6), { tone: "mid", crease: "lo" }));
  out.push(L(k.sideArc(x, y, r, cellZ + 0.6 * MM, P, 48), { tone: "faint" }));
  const top = cellZ + cellH;
  out.push(L(k.ring(x, y, r - 1.0 * MM, top, P, 64), { tone: "faint" }));
  out.push(k.faceTextSvg(k.topMatrix([x, y + 4 * MM], top, P, "x"), label, { size: 2.6, tone: "lo", anchor: "middle" }));
  const clip = { x: x - 1.8 * MM, y: plus[1] - 0.8 * MM, w: 3.6 * MM, d: y - plus[1] + 0.8 * MM, r: 0.5 * MM };
  out.push(S(k.slabOf({ x: clip.x, y: clip.y, w: clip.w, d: 1.4 * MM, r: 0.3 * MM }, 0, top + 0.4 * MM, P, 2), { tone: "mid", crease: "none" }));
  out.push(S(k.slabOf(clip, top, 0.4 * MM, P, 3, 0.3), { tone: "mid", crease: "lo" }));
  out.push(D([k.iso([x, y - 1.2 * MM, top + 0.4 * MM], P)], { size: 0.5, tone: "mid" }));
  out.push(k.faceTextSvg(k.topMatrix([x, y - 4.6 * MM], top + 0.4 * MM, P, "x"), "+", { size: 3.2, tone: "lo", anchor: "middle" }));
  return { svg: out.join(""), plus, minus };
}

// A small moving-coil panel meter standing on the board, its dial on the +y
// face. Two pins drop out of its front foot into pads. Returns
// { svg, needle(fraction), pins } where needle gives the pointer path for a
// deflection from 0 (left stop) to 1 (full scale).
export function panelMeter({ x, y, w = 22 * MM, d = 8 * MM, h = 17 * MM, span = 50, ticks = 21, every = 5 }, P) {
  const plan = { x: x - w / 2, y: y - d / 2, w, d, r: 0.8 * MM };
  const face = y + d / 2 + 0.6 * MM;
  const pins = [[x - w / 4, face + 1.6 * MM], [x + w / 4, face + 1.6 * MM]];
  const out = pins.map(([px, py]) => pad(px, py, P, { lead: 0.35 * MM }));
  for (const [px, py] of pins) out.push(S(k.slabOf({ x: px - 0.6 * MM, y: face - 0.6 * MM, w: 1.2 * MM, d: py - face + 0.6 * MM, r: 0.1 * MM }, 0, 0.4 * MM, P, 2), { tone: "hi", crease: "none" }));
  out.push(S(k.slabOf(plan, 0, h, P, 4, 0.6), { tone: "mid" }));
  const bezel = { x: plan.x + 1 * MM, y: y + d / 2, w: w - 2 * MM, d: 0.6 * MM, r: 0.2 * MM };
  out.push(S(k.slabOf(bezel, 1.6 * MM, h - 2.6 * MM, P, 2), { tone: "lo", crease: "none" }));
  const dialPlan = { x: plan.x + 2 * MM, y: face, w: w - 4 * MM, d: 0.1, r: 0 };
  out.push(S(k.slabOf(dialPlan, 2.4 * MM, h - 4.2 * MM, P, 1), { tone: "hi", lit: false, crease: "none" }));
  const pivot = [x, face + 0.1, 3.4 * MM];
  const R = 10.4 * MM;
  const at = (f, rad) => {
    const a = ((f - 0.5) * span * Math.PI) / 180;
    return [pivot[0] + Math.sin(a) * rad, pivot[1], pivot[2] + Math.cos(a) * rad];
  };
  const arc = Array.from({ length: 33 }, (_, i) => at(i / 32, R));
  const outer = Array.from({ length: 33 }, (_, i) => at(i / 32, R + 1.6 * MM));
  out.push(L(pathOf(arc, P), { tone: "lo" }), L(pathOf(outer, P), { tone: "faint" }));
  let minor = "", major = "";
  for (let i = 0; i < ticks; i++) {
    const f = i / (ticks - 1);
    const big = i % every === 0;
    const seg = pathOf([at(f, R), at(f, R + (big ? 1.6 : 0.9) * MM)], P);
    if (big) major += seg; else minor += seg;
  }
  out.push(L(minor, { tone: "lo" }), L(major, { tone: "mid" }));
  out.push(S(k.slabOf({ x: pivot[0] - 1.6 * MM, y: face, w: 3.2 * MM, d: 0.8 * MM, r: 0.6 * MM }, 2.4 * MM, 2 * MM, P, 3), { tone: "mid", crease: "none" }));
  out.push(k.faceTextSvg(k.sideMatrix([x, face + 0.12], pivot[2] + 4.2 * MM, P, "left"), "mA", { size: 2.4, tone: "lo", anchor: "middle" }));
  const needle = (f) => pathOf([at(f, -1.0 * MM), at(Math.min(1, Math.max(0, f)), R + 0.4 * MM)].map(([px, , pz]) => [px, face + 0.9 * MM, pz]), P);
  for (const [dx] of [[-1], [1]]) out.push(D([k.iso([x + dx * (w / 2 - 1.6 * MM), y + d / 2, h - 1.2 * MM], P)], { size: 0.45, tone: "lo" }));
  return { svg: out.join(""), needle, pins, face, pivot, R, at };
}
