import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import * as k from "../../../anatomy/kit/iso-kit.mjs";
import { kitScript } from "../../../anatomy/scripts/inline-kit.mjs";
import * as E from "../../kit/electronics.mjs";
import * as M from "../../kit/circuit.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const theme = process.argv.includes("--light") ? "light" : "dark";
const { MM } = E;

// ---- Truth -----------------------------------------------------------------
// A CR2032 (3.0 V, about 15 Ω inside) drives a red LED through a 47 Ω resistor
// and a 1 kΩ potentiometer. Turning the knob right lowers the pot's
// resistance, so more current flows and the LED gets brighter.
const CIRCUIT = { volts: 3.0, cell: 15, fixed: 47, pot: 1000, fullScale: 0.02 };
const ohmsAt = (turn) => CIRCUIT.cell + CIRCUIT.fixed + (1 - turn) * CIRCUIT.pot;
const dim = M.seriesLed({ volts: CIRCUIT.volts, ohms: ohmsAt(0) });
const bright = M.seriesLed({ volts: CIRCUIT.volts, ohms: ohmsAt(1) });

// ---- World -----------------------------------------------------------------
const WIDTH = 600;
const HEIGHT = 400;
const BOARD = { x: -128, y: -88, w: 256, d: 176, r: 3 * MM };

const CELL = { x: -84, y: 4 };
const POT = { x: -6, y: 36 };
const RES = { from: 10, to: 50, y: -22 };
const METER = { x: 66, y: -60 };
const LED = { x: 82, y: 30 };
const CAP = { x: -56, y: -70, pitch: 2 * MM };

const P = k.fitProjection(
  [...k.boxCorners(BOARD, -1.6 * MM - 8 * MM, 0), [METER.x - 44, METER.y, 17 * MM], [METER.x + 44, METER.y, 17 * MM], [POT.x, POT.y, 16 * MM]],
  WIDTH,
  HEIGHT,
  { pad: 26, azimuth: 40 },
);
const depth = ([x, y]) => k.depthOf([x, y, 0], P);

const cell = E.coinCell({ ...CELL }, P);
const pot = E.potentiometer({ ...POT }, P);
const meter = E.panelMeter({ ...METER }, P);
const led = E.led({ ...LED }, P);
const capPads = [[CAP.x - CAP.pitch / 2, CAP.y], [CAP.x + CAP.pitch / 2, CAP.y]];
const anode = [LED.x - E.PITCH / 2, LED.y];
const cathode = [LED.x + E.PITCH / 2, LED.y];
const [pinA, wiper] = pot.pins;
const [meterPlus, meterMinus] = meter.pins;

// Every trace is drawn in the direction conventional current flows.
const routes = [
  [cell.plus, [cell.plus[0], -62], [-32, -62], [-32, 72], [pinA[0], 72], pinA],
  [[capPads[0][0], -62], capPads[0]],
  [wiper, [wiper[0], 76], [22, 76], [22, -8], [RES.from, -8], [RES.from, RES.y]],
  [[RES.to, RES.y], [RES.to, -29], [meterPlus[0], -29], meterPlus],
  [meterMinus, [meterMinus[0], -14], [70, -14], [70, LED.y], anode],
  [cathode, [104, LED.y], [104, 64]],
  [capPads[1], [capPads[1][0], -78], [-40, -78]],
  [[-48, cell.minus[1]], cell.minus],
];
const vias = [[104, 64], [-40, -78], [-48, cell.minus[1]]];
const loop = new Set([0, 2, 3, 4, 5, 7]);
const traces = routes.map((points, i) => E.trace(points, P, { flow: loop.has(i) ? `t${i}` : null }));

const parts = [
  { at: [METER.x, METER.y], svg: meter.svg + `<path data-part="needle" class="iso-line" data-tone="lit" data-free="both" d="${meter.needle(0)}" style="stroke-width:0.9"/>` },
  { at: [CAP.x, CAP.y], svg: E.electrolytic({ x: CAP.x, y: CAP.y, pitch: CAP.pitch }, P) },
  { at: [CELL.x, CELL.y], svg: cell.svg },
  { at: [(RES.from + RES.to) / 2, RES.y], svg: E.resistor({ ...RES, bands: E.colourCode(CIRCUIT.fixed) }, P) },
  { at: [POT.x, POT.y], svg: pot.svg + `<path data-part="pointer" class="iso-line" data-tone="lit" data-free="end" d="${pot.pointer(0)}" style="stroke-width:1.1"/>` },
  { at: [LED.x, LED.y], svg: led.svg },
].sort((a, b) => depth(a.at) - depth(b.at));

// Small silkscreen marks: a plus by the LED anode and the cell's plus pad.
const silk = [
  k.lineOnTop([anode[0] - 2 * MM, LED.y - 4 * MM], [anode[0] - 0.8 * MM, LED.y - 4 * MM], 0.05, P),
  k.lineOnTop([anode[0] - 1.4 * MM, LED.y - 4.6 * MM], [anode[0] - 1.4 * MM, LED.y - 3.4 * MM], 0.05, P),
].join("");

const svg = k.figureSvg({
  width: WIDTH,
  height: HEIGHT,
  label: `A small circuit board on four standoffs. A coin cell drives a red LED through a ${CIRCUIT.fixed} ohm resistor, a 1 kilohm knob and a panel ammeter. Turning the knob changes the resistance in the loop, the meter needle shows the current and the LED glows brighter or dimmer.`,
  body: [
    E.ELEC_DEFS,
    E.board(BOARD, P),
    traces.map((t) => t.svg).join(""),
    vias.map(([x, y]) => E.via(x, y, P)).join(""),
    `<path class="iso-line" data-tone="lo" d="${silk}"/>`,
    `<g data-part="flow">${traces.map((t) => t.flow).join("")}</g>`,
    parts.map((p) => p.svg).join(""),
    led.glow,
  ],
});

// ---- Live ------------------------------------------------------------------
const live = `
${M.ledVoltage.toString()}
${M.seriesLed.toString()}
${M.eng.toString()}
const RED_LED = ${JSON.stringify(M.RED_LED)};
const P = ${JSON.stringify(P)};
const C = ${JSON.stringify(CIRCUIT)};
const POT = ${JSON.stringify({ ...POT, knobR: 3.2 * MM, top: pot.top, MM })};
const METER = ${JSON.stringify({ pivot: meter.pivot, R: meter.R, face: meter.face, span: 50, MM })};
const stage = document.querySelector(".iso-stage");
const svg = stage.querySelector("svg");
const pointer = svg.querySelector('[data-part="pointer"]');
const needle = svg.querySelector('[data-part="needle"]');
const glow = svg.querySelector('[data-part="glow"]');
const lens = svg.querySelector('[data-part="led"]');
const flows = [...svg.querySelectorAll(".el-flow")];
const readout = document.querySelector("[data-readout]");
const still = matchMedia("(prefers-reduced-motion: reduce)");
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const ohmsAt = (turn) => C.cell + C.fixed + (1 - turn) * C.pot;
const pointerAt = (turn) => {
  const a = -Math.PI * 5 / 6 + turn * Math.PI * 5 / 3;
  const r0 = 1.2 * POT.MM, r1 = POT.knobR - 0.8 * POT.MM;
  return lineOnTop([POT.x + Math.sin(a) * r0, POT.y - Math.cos(a) * r0], [POT.x + Math.sin(a) * r1, POT.y - Math.cos(a) * r1], POT.top, P);
};
const needleAt = (f) => {
  const at = (g, rad) => { const a = (g - 0.5) * METER.span * Math.PI / 180; return [METER.pivot[0] + Math.sin(a) * rad, METER.face + 0.9 * METER.MM, METER.pivot[2] + Math.cos(a) * rad]; };
  return segment(at(f, -1.0 * METER.MM), at(clamp(f, 0, 1), METER.R + 0.4 * METER.MM), P);
};
const stops = [0.15, 0.55, 1, 0.75, 0.3, 0];
let turn = 0, target = 0, gauge = { at: 0, rate: 0 }, drift = 0;
let frame = 0, last = 0, clock = 0, touring = true, visible = false, idleTimer = 0;
function draw(state) {
  pointer.setAttribute("d", pointerAt(turn));
  needle.setAttribute("d", needleAt(gauge.at / C.fullScale));
  const glowLevel = Math.sqrt(clamp(state.amps / C.fullScale, 0, 1));
  glow.setAttribute("opacity", glowLevel.toFixed(3));
  lens.style.setProperty("--el-on", glowLevel.toFixed(3));
  for (const el of flows) el.style.strokeDashoffset = (-drift).toFixed(2);
  const text = "knob " + eng((1 - turn) * C.pot, "Ω") + " · " + eng(state.amps, "A") + " · LED " + state.vf.toFixed(2) + " V";
  if (readout.textContent !== text) readout.textContent = text;
  stage.setAttribute("aria-valuenow", String(Math.round(turn * 100)));
  stage.setAttribute("aria-valuetext", text);
}
function tick(now) {
  const dt = last ? Math.min((now - last) / 1000, 1 / 30) : 1 / 60;
  last = now;
  const calm = still.matches;
  if (touring) { clock += dt; target = stops[Math.floor(clock / 2.4) % stops.length]; }
  turn = calm ? target : turn + (target - turn) * (1 - Math.exp(-dt / 0.35));
  if (Math.abs(target - turn) < 0.0005) turn = target;
  const state = seriesLed({ volts: C.volts, ohms: ohmsAt(turn), led: RED_LED });
  // The meter movement is a damped spring, like a real moving coil.
  const stiff = 160, drag = calm ? 2 * Math.sqrt(160) : 14;
  for (let i = 0; i < 4; i++) { gauge.rate += ((state.amps - gauge.at) * stiff - gauge.rate * drag) * dt / 4; gauge.at += gauge.rate * dt / 4; }
  if (Math.abs(state.amps - gauge.at) < 1e-6 && Math.abs(gauge.rate) < 1e-5) { gauge.at = state.amps; gauge.rate = 0; }
  // Dots drift along the traces at a speed proportional to the current.
  if (!calm) drift = (drift + dt * 900 * state.amps) % 1000;
  draw(state);
  frame = visible ? requestAnimationFrame(tick) : 0;
}
const run = () => { if (!frame && visible) { last = 0; frame = requestAnimationFrame(tick); } };
const steer = (next) => { touring = false; target = clamp(next, 0, 1); clearTimeout(idleTimer); idleTimer = setTimeout(() => { touring = !still.matches; clock = 0; run(); }, 3600); run(); };
new IntersectionObserver((entries) => { visible = entries[entries.length - 1].isIntersecting; if (visible) run(); }, { rootMargin: "120px 0px" }).observe(stage);
if (still.matches) touring = false;
stage.addEventListener("pointermove", (event) => {
  const box = svg.getBoundingClientRect();
  steer(clamp(((event.clientX - box.left) / box.width - 0.2) / 0.6, 0, 1));
});
stage.addEventListener("keydown", (event) => {
  const step = event.shiftKey ? 0.2 : 0.05;
  let to = null;
  if (event.key === "ArrowRight" || event.key === "ArrowUp") to = target + step;
  if (event.key === "ArrowLeft" || event.key === "ArrowDown") to = target - step;
  if (event.key === "Home") to = 0;
  if (event.key === "End") to = 1;
  if (to === null) return;
  event.preventDefault();
  steer(to);
});
draw(seriesLed({ volts: C.volts, ohms: ohmsAt(0), led: RED_LED }));
`;

const mA = (amps) => (amps * 1000).toFixed(1);
const body = k.plateHtml({
  fig: "Fig 1",
  title: "LED dimmer",
  hint: "Hover to turn the knob",
  readout: `knob ${M.eng(CIRCUIT.pot, "Ω")} · ${M.eng(dim.amps, "A")} · LED ${dim.vf.toFixed(2)} V`,
  keys: [
    { mark: "lit", label: "Knob, needle and moving charge: what changes when you turn it" },
    { mark: "red", label: "The LED, brighter as more current flows" },
    { mark: "dotted", label: "Current along the copper traces" },
  ],
  caption: `A ${CIRCUIT.volts.toFixed(1)} V coin cell, a ${CIRCUIT.fixed} Ω resistor, a 1 kΩ knob, an ammeter and a red LED in one loop. Turned fully left the loop holds about ${ohmsAt(0)} Ω and only ${mA(dim.amps)} mA flows; turned fully right it drops to ${ohmsAt(1)} Ω and ${mA(bright.amps)} mA flows. The LED keeps about ${dim.vf.toFixed(1)} to ${bright.vf.toFixed(1)} V across itself the whole time, so the resistors set the current.`,
  body: `<div class="iso-stage" tabindex="0" role="slider" aria-label="LED dimmer: arrow keys turn the knob" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">${svg}</div>`,
});

const name = theme === "light" ? "led-dimmer-light.html" : "led-dimmer.html";
writeFileSync(join(HERE, name), k.pageHtml({ title: "LED dimmer", theme, body: `<style>${E.ELEC_CSS}</style>` + body, script: kitScript() + live }));
console.log("wrote", name, `· ${mA(dim.amps)} to ${mA(bright.amps)} mA`);
