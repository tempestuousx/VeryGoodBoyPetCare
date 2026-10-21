import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import * as k from "../../../anatomy/kit/iso-kit.mjs";
import { kitScript } from "../../../anatomy/scripts/inline-kit.mjs";
import * as E from "../../kit/electronics.mjs";
import * as M from "../../kit/circuit.mjs";
import * as T from "../../kit/catalog.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const theme = process.argv.includes("--light") ? "light" : "dark";
const { MM } = E;

// ---- Truth -----------------------------------------------------------------
// A CR2032 (3.0 V, about 15 Ω inside) drives a red LED through a 47 Ω resistor
// and a 1 kΩ potentiometer. Turning the knob right lowers the pot's
// resistance, so more current flows and the LED gets brighter.
const pick = (id) => T.CATALOG.find((part) => part.id === id);
const START = { cell: pick("cr2032"), res: pick("r47"), pot: pick("p1k"), led: pick("red"), meter: pick("m20"), cap: pick("c10") };
const dim = T.verdict.call(null, START, 0);

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

// Each part is a clickable group: data-id names its slot, data-cat its function.
const part = (id, svg) => `<g class="el-part" data-id="${id}" data-cat="${T.SLOTS[id].cat}">${svg}</g>`;
const parts = [
  { id: "meter", at: [METER.x, METER.y], svg: meter.svg + `<path data-part="needle" class="iso-line" data-tone="lit" data-free="both" d="${meter.needle(0)}" style="stroke-width:0.9"/>` },
  { id: "cap", at: [CAP.x, CAP.y], svg: E.electrolytic({ x: CAP.x, y: CAP.y, pitch: CAP.pitch }, P) },
  { id: "cell", at: [CELL.x, CELL.y], svg: cell.svg },
  { id: "res", at: [(RES.from + RES.to) / 2, RES.y], svg: E.resistor({ ...RES, bands: E.colourCode(START.res.ohms) }, P) },
  { id: "pot", at: [POT.x, POT.y], svg: pot.svg + `<path data-part="pointer" class="iso-line" data-tone="lit" data-free="end" d="${pot.pointer(0)}" style="stroke-width:1.1"/>` },
  { id: "led", at: [LED.x, LED.y], svg: led.svg },
].sort((a, b) => depth(a.at) - depth(b.at));

// Small silkscreen marks: a plus by the LED anode.
const silk = [
  k.lineOnTop([anode[0] - 2 * MM, LED.y - 4 * MM], [anode[0] - 0.8 * MM, LED.y - 4 * MM], 0.05, P),
  k.lineOnTop([anode[0] - 1.4 * MM, LED.y - 4.6 * MM], [anode[0] - 1.4 * MM, LED.y - 3.4 * MM], 0.05, P),
].join("");

const svg = k.figureSvg({
  width: WIDTH,
  height: HEIGHT,
  label: "A small circuit board on four standoffs. A coin cell drives a red LED through a 47 ohm resistor, a 1 kilohm knob and a panel ammeter. Click a part to learn what it is, remove it or swap it, and see whether the circuit still works.",
  body: [
    E.ELEC_DEFS,
    part("board", E.board(BOARD, P)),
    part("traces", traces.map((t) => t.svg).join("") + vias.map(([x, y]) => E.via(x, y, P)).join("")),
    `<path class="iso-line" data-tone="lo" d="${silk}"/>`,
    `<g data-part="flow">${traces.map((t) => t.flow).join("")}</g>`,
    parts.map((p) => part(p.id, p.svg)).join(""),
    led.glow,
  ],
});

// ---- Tinker panel ----------------------------------------------------------
const legend = Object.entries(T.CATEGORIES).map(([id, c]) => `<span class="el-chip" data-cat="${id}">${c.label}</span>`).join("");
const panel = `
<div class="el-panel">
  <div class="el-row">
    <label class="el-knob">Knob <input type="range" min="0" max="100" value="0" data-knob></label>
    <button data-act="colors" aria-pressed="false">Colour by function</button>
    <button data-act="apart" aria-pressed="false">Take apart</button>
    <button data-act="reset">Reset</button>
  </div>
  <div class="el-verdict" data-verdict></div>
  <div class="el-legend" hidden>${legend}</div>
  <div class="el-info" data-info><b>Click any part</b> to see what it is, remove it or swap it.</div>
  <div class="el-search">
    <input type="search" placeholder="Search parts: 9V, 220, blue LED, jumper…" data-search aria-label="Search parts">
    <ul data-results></ul>
  </div>
</div>`;

const catCss = Object.entries(T.CATEGORIES).map(([id, c]) => `.iso [data-cat="${id}"]{--cat:${c.color}}.iso[data-theme="light"] [data-cat="${id}"]{--cat:${c.light}}`).join("");
const PANEL_CSS = `${catCss}
.el-part{cursor:pointer}.el-part[data-removed]{display:none}
.iso[data-colors] .el-part .iso-edge{stroke:var(--cat)}
.iso[data-colors] .el-part .iso-top{fill:color-mix(in srgb,var(--cat) 35%,var(--anatomy-top))}
${[0, 1, 2, 3].map((n) => `.iso[data-colors] .el-part .iso-shade[data-shade="${n}"]{fill:color-mix(in srgb,var(--cat) 22%,var(--anatomy-shade-${n}))}`).join("")}
.iso[data-colors] .el-trace{stroke:var(--cat);opacity:.9}
.el-part[data-selected] .iso-edge{stroke:var(--anatomy-lit);stroke-width:1.4}
.el-panel{display:grid;gap:10px;margin-top:14px;font-size:13px;color:var(--anatomy-text)}
.el-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.el-panel button,.el-panel input[type=search]{font:inherit;color:var(--anatomy-strong);background:var(--anatomy-card);border:1px solid var(--anatomy-lo);border-radius:6px;padding:6px 10px}
.el-panel button{cursor:pointer}.el-panel button[aria-pressed=true]{border-color:var(--anatomy-hi)}
.el-knob{display:flex;gap:8px;align-items:center;flex:1 1 160px}.el-knob input{flex:1}
.el-verdict{padding:8px 10px;border-radius:6px;border-left:3px solid var(--anatomy-green)}
.el-verdict[data-level=warn]{border-color:#f5a524}.el-verdict[data-level=bad]{border-color:var(--anatomy-red)}
.el-legend{display:flex;flex-wrap:wrap;gap:6px}
.el-chip{padding:2px 8px;border-radius:99px;border:1px solid var(--cat);color:var(--cat)}
.el-info{line-height:1.5}.el-info .el-chip{margin-left:6px}
.el-search input{width:100%;box-sizing:border-box}
.el-search ul{list-style:none;margin:6px 0 0;padding:0;display:grid;gap:4px;max-height:180px;overflow:auto}
.el-search li button{width:100%;text-align:left}
.el-search li small{color:var(--anatomy-muted)}`;

// ---- Live ------------------------------------------------------------------
const live = `
${M.ledVoltage.toString()}
${M.seriesLed.toString()}
${M.eng.toString()}
${E.colourCode.toString()}
${T.verdict.toString()}
const SLOTS = ${JSON.stringify(T.SLOTS)};
const CATEGORIES = ${JSON.stringify(T.CATEGORIES)};
const CATALOG = ${JSON.stringify(T.CATALOG)};
const TAKE_APART = ${JSON.stringify(T.TAKE_APART)};
const START = ${JSON.stringify(Object.fromEntries(Object.entries(START).map(([s, p]) => [s, p.id])))};
const P = ${JSON.stringify(P)};
const POT = ${JSON.stringify({ ...POT, knobR: 3.2 * MM, top: pot.top, MM })};
const METER = ${JSON.stringify({ pivot: meter.pivot, R: meter.R, face: meter.face, span: 50, MM })};
const root = document.querySelector(".iso");
const stage = document.querySelector(".iso-stage");
const svg = stage.querySelector("svg");
const $ = (s) => document.querySelector(s);
const group = (id) => svg.querySelector('.el-part[data-id="' + id + '"]');
const pointer = svg.querySelector('[data-part="pointer"]');
const needle = svg.querySelector('[data-part="needle"]');
const glow = svg.querySelector('[data-part="glow"]');
const lens = svg.querySelector('[data-part="led"]');
const flows = [...svg.querySelectorAll(".el-flow")];
const readout = document.querySelector("[data-readout]");
const still = matchMedia("(prefers-reduced-motion: reduce)");
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const byId = (id) => CATALOG.find((p) => p.id === id);
let parts = {}, selected = null, apart = 0, apartTarget = 0;
const pointerAt = (turn) => {
  const a = -Math.PI * 5 / 6 + turn * Math.PI * 5 / 3;
  const r0 = 1.2 * POT.MM, r1 = POT.knobR - 0.8 * POT.MM;
  return lineOnTop([POT.x + Math.sin(a) * r0, POT.y - Math.cos(a) * r0], [POT.x + Math.sin(a) * r1, POT.y - Math.cos(a) * r1], POT.top, P);
};
const needleAt = (f) => {
  const at = (g, rad) => { const a = (g - 0.5) * METER.span * Math.PI / 180; return [METER.pivot[0] + Math.sin(a) * rad, METER.face + 0.9 * METER.MM, METER.pivot[2] + Math.cos(a) * rad]; };
  return segment(at(f, -1.0 * METER.MM), at(clamp(f, 0, 1), METER.R + 0.4 * METER.MM), P);
};

// Put a catalog part (or null to remove) in its slot and redraw what it changes.
function install(slot, entry) {
  parts[slot] = entry;
  const g = group(slot);
  g.toggleAttribute("data-removed", !entry);
  if (!entry) return;
  if (slot === "res") g.querySelectorAll(".el-band").forEach((b, i) => b.setAttribute("data-c", entry.ohms ? colourCode(entry.ohms)[i] : "0"));
  if (slot === "led") { svg.style.setProperty("--el-led", entry.color); svg.style.setProperty("--el-led-core", entry.core); }
  if (slot === "cell") { const t = g.querySelector(".iso-face-text"); if (t) t.textContent = entry.label; }
}
function reset() { for (const [slot, id] of Object.entries(START)) install(slot, byId(id)); select(null); }

function select(id) {
  selected = id;
  svg.querySelectorAll(".el-part").forEach((g) => g.toggleAttribute("data-selected", g.dataset.id === id));
  const info = $("[data-info]");
  if (!id) { info.innerHTML = "<b>Click any part</b> to see what it is, remove it or swap it."; return; }
  const s = SLOTS[id], c = CATEGORIES[s.cat], now = parts[id];
  const step = TAKE_APART.indexOf(id);
  info.innerHTML = "<b>" + s.what + "</b>" + (now ? " · " + now.name : "") + '<span class="el-chip" data-cat="' + s.cat + '">' + c.label + "</span><br>" + s.does +
    "<br><small>" + (s.series ? "Needed: it is in the only loop." : "Not in the current loop.") + (step >= 0 ? " Take-apart step " + (step + 1) + ": " : " ") + s.takeApart + "</small>" +
    (id in START ? '<div class="el-row" style="margin-top:6px"><button data-act="toggle">' + (now ? "Remove it" : "Put it back") + '</button><button data-act="swap">Swap for…</button></div>' : "");
}

function search(text) {
  const words = text.toLowerCase().split(/\\s+/).filter(Boolean);
  const list = CATALOG.filter((p) => { const hay = (p.name + " " + p.slot + " " + SLOTS[p.slot].what).toLowerCase(); const tight = hay.replace(/\\s/g, ""); return words.every((w) => hay.includes(w) || tight.includes(w)); }).slice(0, 12);
  $("[data-results]").innerHTML = text ? list.map((p) => '<li><button data-put="' + p.id + '">' + p.name + " <small>→ " + SLOTS[p.slot].what + (parts[p.slot] && parts[p.slot].id === p.id ? " (fitted)" : "") + "</small></button></li>").join("") : "";
}

let turn = 0, target = 0, gauge = { at: 0, rate: 0 }, drift = 0;
let frame = 0, last = 0, clock = 0, touring = true, visible = false;
const stops = [0.15, 0.55, 1, 0.75, 0.3, 0];
function tick(now) {
  const dt = last ? Math.min((now - last) / 1000, 1 / 30) : 1 / 60;
  last = now;
  const calm = still.matches;
  if (touring) { clock += dt; target = stops[Math.floor(clock / 2.4) % stops.length]; }
  turn = calm ? target : turn + (target - turn) * (1 - Math.exp(-dt / 0.35));
  apart = calm ? apartTarget : apart + (apartTarget - apart) * (1 - Math.exp(-dt / 0.4));
  // Taken apart means the battery is out, so nothing flows.
  const v = apartTarget ? { amps: 0, vf: 0, level: "warn", say: "Taken apart. Steps in order: " + TAKE_APART.map((s, i) => i + 1 + ". " + SLOTS[s].what).join(", ") + ". Power always comes out first." } : verdict(parts, turn);
  const full = parts.meter && parts.meter.fullScale ? parts.meter.fullScale : 0.02;
  const stiff = 160, drag = calm ? 2 * Math.sqrt(160) : 14;
  for (let i = 0; i < 4; i++) { gauge.rate += ((v.amps - gauge.at) * stiff - gauge.rate * drag) * dt / 4; gauge.at += gauge.rate * dt / 4; }
  if (!calm) drift = (drift + dt * 900 * Math.min(v.amps, 0.05)) % 1000;
  draw(v, full);
  frame = visible ? requestAnimationFrame(tick) : 0;
}
function draw(v, full) {
  pointer.setAttribute("d", pointerAt(turn));
  needle.setAttribute("d", needleAt(gauge.at / full));
  const burnt = v.amps > 0.03;
  const level = burnt ? 0 : Math.sqrt(clamp(v.amps / 0.02, 0, 1));
  glow.setAttribute("opacity", parts.led ? level.toFixed(3) : 0);
  lens.style.setProperty("--el-on", level.toFixed(3));
  for (const el of flows) el.style.strokeDashoffset = (-drift).toFixed(2);
  TAKE_APART.forEach((slot, i) => { const g = group(slot); if (g) g.setAttribute("transform", translateAlong(P, [0, 0, apart * (46 - i * 5)])); });
  const text = "knob " + (parts.pot ? eng(Math.round((1 - turn) * parts.pot.ohms), "Ω") : "—") + " · " + eng(v.amps, "A") + " · LED " + v.vf.toFixed(2) + " V";
  if (readout.textContent !== text) readout.textContent = text;
  const box = $("[data-verdict]");
  if (box.textContent !== v.say) { box.textContent = v.say; box.dataset.level = v.level; }
  stage.setAttribute("aria-valuetext", text);
}
const run = () => { if (!frame && visible) { last = 0; frame = requestAnimationFrame(tick); } };
const hold = () => { touring = false; run(); };
new IntersectionObserver((entries) => { visible = entries[entries.length - 1].isIntersecting; if (visible) run(); }, { rootMargin: "120px 0px" }).observe(stage);
if (still.matches) touring = false;

svg.addEventListener("click", (e) => { const g = e.target.closest(".el-part"); select(g ? g.dataset.id : null); hold(); });
$("[data-knob]").addEventListener("input", (e) => { target = e.target.value / 100; hold(); });
stage.addEventListener("keydown", (event) => {
  const step = event.shiftKey ? 0.2 : 0.05;
  const keys = { ArrowRight: step, ArrowUp: step, ArrowLeft: -step, ArrowDown: -step };
  if (!(event.key in keys)) return;
  event.preventDefault();
  target = clamp(target + keys[event.key], 0, 1); $("[data-knob]").value = target * 100; hold();
});
document.querySelector(".el-panel").addEventListener("click", (e) => {
  const b = e.target.closest("button"); if (!b) return;
  const act = b.dataset.act;
  if (act === "colors") { const on = !root.hasAttribute("data-colors"); root.toggleAttribute("data-colors", on); b.setAttribute("aria-pressed", on); $(".el-legend").hidden = !on; }
  if (act === "apart") { apartTarget = apartTarget ? 0 : 1; b.setAttribute("aria-pressed", !!apartTarget); }
  if (act === "reset") { reset(); apartTarget = 0; }
  if (act === "toggle") { install(selected, parts[selected] ? null : byId(START[selected])); select(selected); }
  if (act === "swap") { const s = $("[data-search]"); s.value = SLOTS[selected].what; search(s.value); s.focus(); }
  if (b.dataset.put) { const p = byId(b.dataset.put); install(p.slot, p); select(p.slot); search($("[data-search]").value); }
  hold();
});
$("[data-search]").addEventListener("input", (e) => search(e.target.value));
reset();
draw(verdict(parts, 0), 0.02);
`;

const mA = (amps) => (amps * 1000).toFixed(1);
const bright = T.verdict(START, 1);
const body = k.plateHtml({
  fig: "Fig 1",
  title: "LED dimmer",
  hint: "Click a part · arrows turn the knob",
  readout: `knob ${M.eng(START.pot.ohms, "Ω")} · ${M.eng(dim.amps, "A")} · LED ${dim.vf.toFixed(2)} V`,
  keys: [
    { mark: "lit", label: "Knob, needle and moving charge: what changes when you turn it" },
    { mark: "red", label: "The LED, brighter as more current flows" },
    { mark: "dotted", label: "Current along the copper traces" },
  ],
  caption: `A ${START.cell.volts.toFixed(1)} V coin cell, a ${START.res.ohms} Ω resistor, a 1 kΩ knob, an ammeter and a red LED in one loop: ${mA(dim.amps)} mA with the knob left, ${mA(bright.amps)} mA with it right. Click a part to learn what it does, remove it or swap it from the catalog, and the panel says whether the circuit still works and why. Swapped parts keep the same drawing; only their values change.`,
  body: `<div class="iso-stage" tabindex="0" role="slider" aria-label="LED dimmer: arrow keys turn the knob, click parts to inspect them" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">${svg}</div>`,
});

const name = theme === "light" ? "led-dimmer-light.html" : "led-dimmer.html";
writeFileSync(join(HERE, name), k.pageHtml({ title: "LED dimmer", theme, body: `<style>${E.ELEC_CSS}${PANEL_CSS}</style>` + body + panel, script: kitScript() + live }));
console.log("wrote", name, `· ${mA(dim.amps)} to ${mA(bright.amps)} mA`);
