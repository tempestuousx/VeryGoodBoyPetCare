// Tinker mode: what each part is, a catalog of swappable parts, and a verdict
import { seriesLed, eng } from "./circuit.mjs";
// on whether the circuit still works. Pure data and functions, so a page can
// inline them with toString() / JSON.stringify().

// Function categories and their colours (used when "colour by function" is on).
export const CATEGORIES = {
  power: { label: "Power", color: "#f5a524", light: "#c27c00" },
  conductor: { label: "Conductor", color: "#e08a4a", light: "#b5652a" },
  control: { label: "Control", color: "#3e9bff", light: "#1f6fd1" },
  resistance: { label: "Resistance", color: "#30c47c", light: "#1f8a55" },
  output: { label: "Output", color: "#ff5a6a", light: "#d1303f" },
  measure: { label: "Measurement", color: "#a77bff", light: "#7748d6" },
  storage: { label: "Storage / filter", color: "#22c3b4", light: "#108a7f" },
  structure: { label: "Structure", color: "#9a9aa0", light: "#6a6a70" },
};

// One entry per slot in the figure: what it is, what it does, whether the
// circuit needs it, and how to take it out.
export const SLOTS = {
  cell: { cat: "power", series: true, what: "Battery", does: "Pushes charge around the loop. Its voltage is the pressure, its internal resistance limits how much it can deliver.", takeApart: "Slide the cell out from under the spring clip. Always remove power first." },
  pot: { cat: "control", series: true, what: "Potentiometer (knob)", does: "A resistor you can adjust. Turning it right lowers its resistance so more current flows.", takeApart: "Pull the knob off its shaft, then desolder the three legs (heat each pad, lift with solder wick)." },
  res: { cat: "resistance", series: true, what: "Fixed resistor", does: "Limits current even when the knob is at zero, so the LED can never get too much.", takeApart: "Heat one pad and pull that lead out, then the other. Straighten the leads to reuse it." },
  meter: { cat: "measure", series: true, what: "Ammeter", does: "Measures the current flowing through it. It sits in series, so the current must pass through it.", takeApart: "Desolder its two pins, then lift it off. Replace it with a jumper wire or the loop opens." },
  led: { cat: "output", series: true, what: "LED", does: "Turns current into light. It only lets current flow one way (the long leg is +) and needs about 2 V before it lights.", takeApart: "Note which leg is + (long leg, round side of the rim), then desolder both legs." },
  cap: { cat: "storage", series: false, what: "Capacitor", does: "Stores a little charge across the battery to smooth sudden changes. The LED loop works without it.", takeApart: "Note the stripe (that is the - leg), then desolder both legs." },
  traces: { cat: "conductor", series: false, what: "Copper traces", does: "The wires of the board. Current flows along them from part to part. Vias carry it to the copper on the back.", takeApart: "Traces are part of the board and do not come off." },
  board: { cat: "structure", series: false, what: "Circuit board", does: "Holds the parts and the copper. Standoffs keep it off the table.", takeApart: "Remove every part, then unscrew the four nuts to free it from the standoffs." },
};

// The order to take it apart: power first, then the parts nearest the top.
export const TAKE_APART = ["cell", "led", "res", "pot", "meter", "cap"];

// Parts you can search for and drop in. `slot` says where it goes.
export const CATALOG = [
  { id: "cr2032", slot: "cell", name: "CR2032 coin cell", label: "CR2032", volts: 3.0, ohms: 15 },
  { id: "aa", slot: "cell", name: "AA alkaline cell (1.5 V)", label: "AA 1.5V", volts: 1.5, ohms: 0.15 },
  { id: "2aa", slot: "cell", name: "2 × AA pack (3 V)", label: "2xAA", volts: 3.0, ohms: 0.3 },
  { id: "lipo", slot: "cell", name: "Li-ion cell (3.7 V)", label: "3.7V", volts: 3.7, ohms: 0.1 },
  { id: "9v", slot: "cell", name: "9 V battery", label: "9V", volts: 9, ohms: 1.5 },
  ...[0, 10, 22, 47, 100, 220, 470, 1000, 4700].map((ohms) => ({ id: `r${ohms}`, slot: "res", name: ohms ? `Resistor ${ohms >= 1000 ? ohms / 1000 + " k" : ohms + " "}Ω` : "Jumper wire (0 Ω) in place of the resistor", ohms })),
  { id: "p100", slot: "pot", name: "Potentiometer 100 Ω", ohms: 100 },
  { id: "p1k", slot: "pot", name: "Potentiometer 1 kΩ", ohms: 1000 },
  { id: "p10k", slot: "pot", name: "Potentiometer 10 kΩ", ohms: 10000 },
  { id: "red", slot: "led", name: "Red LED", vf0: 2.0, color: "#ff5a4f", core: "#ffd2c8" },
  { id: "yellow", slot: "led", name: "Yellow LED", vf0: 2.1, color: "#ffc83d", core: "#fff1c4" },
  { id: "green", slot: "led", name: "Green LED", vf0: 3.0, color: "#3ddc84", core: "#d4ffe6" },
  { id: "blue", slot: "led", name: "Blue LED", vf0: 3.1, color: "#4d8dff", core: "#d6e6ff" },
  { id: "white", slot: "led", name: "White LED", vf0: 3.1, color: "#f4f4ff", core: "#ffffff" },
  { id: "m20", slot: "meter", name: "Ammeter 0–20 mA", fullScale: 0.02 },
  { id: "m100", slot: "meter", name: "Ammeter 0–100 mA", fullScale: 0.1 },
  { id: "jumper", slot: "meter", name: "Jumper wire in place of the meter", fullScale: 0 },
  { id: "c10", slot: "cap", name: "Capacitor 10 µF" },
  { id: "c100", slot: "cap", name: "Capacitor 100 µF" },
];

// Does it work? `parts` maps slot → catalog entry, or null when removed.
// `turn` is the knob, 0 to 1. Needs seriesLed() and eng() from circuit.mjs.
export function verdict(parts, turn) {
  const missing = Object.keys(parts).filter((slot) => !parts[slot] && SLOTS[slot].series);
  if (missing.length) {
    return { amps: 0, vf: 0, level: "bad", say: `Open circuit: no current flows. The ${missing.map((s) => SLOTS[s].what.toLowerCase()).join(" and ")} ${missing.length > 1 ? "were" : "was"} part of the only loop. A loop must be complete for current to flow.` };
  }
  const { cell, res, pot, led, meter } = parts;
  const ohms = cell.ohms + res.ohms + (1 - turn) * pot.ohms;
  const led0 = { vf0: led.vf0, i0: 0.02, nVt: 0.087 };
  const state = seriesLed({ volts: cell.volts, ohms, led: led0 });
  const notes = [];
  let level = "ok";
  if (state.amps > 0.03) { level = "bad"; notes.push(`LED burns out: ${eng(state.amps, "A")} is over its 30 mA limit. Add resistance.`); }
  else if (state.amps > 0.02) { level = "warn"; notes.push(`LED is over its 20 mA rating (${eng(state.amps, "A")}); it will wear out fast.`); }
  if (state.amps * state.amps * res.ohms > 0.25) { level = "bad"; notes.push("The resistor overheats: it is a 1/4 W part."); }
  if (meter.fullScale && state.amps > meter.fullScale) { level = level === "bad" ? "bad" : "warn"; notes.push("Meter pinned past full scale. Use the 100 mA meter."); }
  if (state.amps < 0.0003 && level === "ok") { level = "warn"; notes.push(cell.volts < led.vf0 ? `Too dim to see: the ${cell.volts} V battery is below the LED's ${led.vf0} V.` : "Too dim to see: too much resistance."); }
  if (!parts.cap) notes.push("No capacitor: still works, the supply is just less smooth.");
  return { ...state, level, say: (level === "ok" ? "Works. " : "") + (notes.join(" ") || `${eng(state.amps, "A")} through the LED.`) };
}
