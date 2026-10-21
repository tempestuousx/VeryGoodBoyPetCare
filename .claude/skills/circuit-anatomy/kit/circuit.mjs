// Small, pure circuit models. Every readout, needle and glow in a figure
// should come from one of these, so the drawing never shows a made-up number.
// Units: volts, ohms, amps, seconds, farads.

// An LED's forward voltage at a current, from the diode law fitted to one
// datasheet point (vf0 at i0) and its slope n·Vt. Defaults are a 5 mm red LED:
// about 2.0 V at 20 mA and 1.8 V near 2 mA.
export const RED_LED = { vf0: 2.0, i0: 0.02, nVt: 0.087 };

export function ledVoltage(i, led = RED_LED) {
  if (i <= 0) return 0;
  return led.vf0 + led.nVt * Math.log(i / led.i0);
}

// A source in series with a resistance and an LED. Solves
// V = I·R + Vf(I) by bisection and returns current, LED voltage, the drop on
// the resistance and the power in each part.
export function seriesLed({ volts, ohms, led = RED_LED }) {
  let lo = 0;
  let hi = volts / Math.max(ohms, 1e-6);
  for (let n = 0; n < 60; n++) {
    const mid = (lo + hi) / 2;
    if (mid * ohms + ledVoltage(mid, led) > volts) hi = mid;
    else lo = mid;
  }
  const amps = (lo + hi) / 2;
  const vf = ledVoltage(amps, led);
  return { amps, vf, drop: amps * ohms, ledWatts: amps * vf, resistorWatts: amps * amps * ohms };
}

// A resistor divider: Vout = Vin·R2 / (R1 + R2).
export const divider = (vin, r1, r2) => (vin * r2) / (r1 + r2);

// An RC network charging toward vin from v0 (or discharging toward 0 when vin
// is 0) after t seconds.
export const rcCharge = (vin, v0, r, c, t) => vin + (v0 - vin) * Math.exp(-t / (r * c));

// Parallel resistances.
export const parallel = (...rs) => 1 / rs.reduce((sum, r) => sum + 1 / r, 0);

// Engineering notation for readouts: 0.0021 → "2.1 m", 4700 → "4.7 k".
export function eng(value, unit = "", digits = 3) {
  if (value === 0) return `0 ${unit}`;
  const prefixes = [[1e9, "G"], [1e6, "M"], [1e3, "k"], [1, ""], [1e-3, "m"], [1e-6, "µ"], [1e-9, "n"], [1e-12, "p"]];
  const [scale, prefix] = prefixes.find(([s]) => Math.abs(value) >= s) || prefixes[prefixes.length - 1];
  const n = value / scale;
  const text = n.toFixed(Math.max(0, digits - 1 - Math.floor(Math.log10(Math.abs(n)))));
  return `${text} ${prefix}${unit}`;
}
