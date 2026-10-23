// MODEL-START
// Re-refinación de aceite de motor usado por etapas. Unidades: kg, K, Pa, s, J.
// Cada etapa recibe una corriente {especie: kg} y regresa productos, residuos, energía y tiempo.

const R = 8.314, PATM = 101325, G = 9.81;

// Especies. Tb: punto de ebullición normal (K); M: kg/mol; nv: no volátil
const SP = {
  W:   { name: 'Agua', M: 0.018 },
  FG:  { name: 'Combustible ligero (gasolina)', Tb: 400, M: 0.10 },
  FD:  { name: 'Combustible ligero (diésel)', Tb: 560, M: 0.23 },
  B1:  { name: 'Base 1', Tb: 650, M: 0.30, v40: 18, v100: 3.9 },
  B2:  { name: 'Base 2', Tb: 690, M: 0.34, v40: 30, v100: 5.2 },
  B3:  { name: 'Base 3', Tb: 720, M: 0.38, v40: 55, v100: 7.5 },
  B4:  { name: 'Base 4', Tb: 760, M: 0.43, v40: 100, v100: 11 },
  B5:  { name: 'Base 5', Tb: 800, M: 0.50, v40: 220, v100: 18 },
  B6:  { name: 'Base 6', Tb: 840, M: 0.58, v40: 500, v100: 32 },
  OXv: { name: 'Productos de oxidación (destilables)', Tb: 740, M: 0.40, polar: true },
  DV:  { name: 'Aditivo descompuesto (destilable)', Tb: 620, M: 0.25, polar: true },
  OXh: { name: 'Productos de oxidación (pesados)', nv: true, polar: true, M: 0.6 },
  AD:  { name: 'Aditivos con metales (detergentes, ZDDP)', nv: true, M: 0.8 },
  VI:  { name: 'Polímeros mejoradores de viscosidad', nv: true, M: 20 },
  SO:  { name: 'Hollín', nv: true },
  PW:  { name: 'Partículas de desgaste y tierra', nv: true },
  IPA: { name: '2-propanol', M: 0.060 },
  REA: { name: 'Reactivos (KOH, DAP o ácido)', nv: true },
  CL:  { name: 'Arcilla', nv: true },
};
const BASE = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6'];
const VOLATILES = ['FG', 'FD', ...BASE, 'OXv', 'DV'];
const IMPUREZAS = ['OXv', 'DV', 'OXh', 'AD', 'VI', 'SO', 'PW'];

// Metales por kg de cada especie (fracción másica): los aditivos llevan Ca, Zn y P; el desgaste Fe, Pb y Si
const METALS = { AD: { Ca: 0.0667, Zn: 0.0333, P: 0.030 }, PW: { Fe: 0.025, Pb: 0.0025, Si: 0.0075 } };
const ASH_FACTOR = 1.6; // ceniza sulfatada ≈ 1.6 × metales

// Aceite usado de entrada, % en masa (mezcla de taller)
const FEEDS = {
  taller:   { W: 6, FG: 2, FD: 3, base: 79.5, OXv: 1.8, OXh: 1.2, AD: 3, VI: 2.5, SO: 0.6, PW: 0.4 },
  gasolina: { W: 4, FG: 4, FD: 1, base: 81.6, OXv: 2.0, OXh: 1.0, AD: 3, VI: 3.0, SO: 0.2, PW: 0.2 },
  diesel:   { W: 5, FG: 0.5, FD: 5, base: 78.3, OXv: 1.6, OXh: 1.4, AD: 3.5, VI: 2.0, SO: 2.2, PW: 0.5 },
  agua:     { W: 15, FG: 2, FD: 3, base: 70.5, OXv: 1.8, OXh: 1.2, AD: 3, VI: 2.5, SO: 0.6, PW: 0.4 },
};
const BASE_SPLIT = { B1: 0.12, B2: 0.23, B3: 0.22, B4: 0.20, B5: 0.15, B6: 0.08 };
const FREE_WATER = 0.6;    // fracción del agua que está libre (gotas); el resto emulsionada
const CP_OIL = 2100, CP_IPA = 2600, LAT_W = 2.257e6, LAT_IPA = 6.63e5, LAT_HC = 2.6e5;

function feedStream(type, mass) {
  const f = FEEDS[type], s = {};
  let tot = 0;
  for (const k in f) tot += f[k];
  for (const k in f) {
    if (k === 'base') for (const b of BASE) s[b] = mass * f.base / tot * BASE_SPLIT[b];
    else s[k] = mass * f[k] / tot;
  }
  for (const k of ['DV', 'IPA', 'REA', 'CL']) s[k] = 0;
  return s;
}

// ---------- utilidades ----------
const sum = (s, keys) => (keys || Object.keys(s)).reduce((a, k) => a + (s[k] || 0), 0);
const copy = (s) => Object.assign({}, s);
const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);
function addTo(dst, src, f = 1) { for (const k in src) dst[k] = (dst[k] || 0) + src[k] * f; return dst; }
function oilMass(s) { return sum(s, [...BASE, 'FG', 'FD', ...IMPUREZAS]); }

// Presión de vapor de fracciones de petróleo: Maxwell–Bonnell (API TDB 5A1.19), Pa
function psatMB(TbK, TK) {
  const Tb = TbK * 1.8, T = TK * 1.8;
  const X = (Tb / T - 0.0002867 * Tb) / (748.1 - 0.2145 * Tb);
  let l = (2663.129 * X - 5.994296) / (95.76 * X - 0.972546);
  if (l < Math.log10(2)) l = (3000.538 * X - 6.761560) / (43 * X - 0.987672);
  return Math.pow(10, l) * 133.322;
}
function psatWater(TK) { const t = TK - 273.15; return Math.pow(10, 8.07131 - 1730.63 / (233.426 + t)) * 133.322; }
function psatIPA(TK) { const t = TK - 273.15; return Math.pow(10, 8.87829 - 2010.33 / (252.636 + t)) * 133.322; }

// Viscosidad: Walther (ASTM D341) entre dos puntos y mezcla con el índice de Refutas
function walther(v40, v100, TK) {
  const a = (v) => Math.log10(Math.log10(v + 0.7));
  const B = (a(v40) - a(v100)) / (Math.log10(373.15) - Math.log10(313.15));
  const A = a(v40) + B * Math.log10(313.15);
  return Math.pow(10, Math.pow(10, A - B * Math.log10(TK))) - 0.7;
}
const vbn = (v) => 14.534 * Math.log(Math.log(v + 0.8)) + 10.975;
const vbnInv = (x) => Math.exp(Math.exp((x - 10.975) / 14.534)) - 0.8;
function blendVisc(s) {
  let m = 0, a40 = 0, a100 = 0;
  for (const b of BASE) { const w = s[b] || 0; m += w; a40 += w * vbn(SP[b].v40); a100 += w * vbn(SP[b].v100); }
  if (m <= 0) return { v40: 0, v100: 0 };
  return { v40: vbnInv(a40 / m), v100: vbnInv(a100 / m) };
}

// Flash ideal (Raoult) con Rachford–Rice; nc = moles de gas que no condensa (agua o N2 de arrastre)
function flash(s, TK, P, nc = 0) {
  const n = {}, K = {};
  let N = nc;
  for (const k of VOLATILES) {
    if (!(s[k] > 0)) continue;
    n[k] = s[k] / SP[k].M; N += n[k]; K[k] = psatMB(SP[k].Tb, TK) / P;
  }
  const keys = Object.keys(n);
  const vap = {}, liq = copy(s);
  if (!keys.length) return { vap, liq };
  const f = (V) => nc / N / V + keys.reduce((a, k) => a + n[k] / N * (K[k] - 1) / ((1 - V) + V * K[k]), 0);
  let V;
  if (f(1) >= 0) V = 1;
  else if (f(1e-9) <= 0) V = 0;
  else { let lo = 1e-9, hi = 1; for (let i = 0; i < 80; i++) { const m = 0.5 * (lo + hi); if (f(m) > 0) lo = m; else hi = m; } V = 0.5 * (lo + hi); }
  for (const k of keys) {
    const fv = V * K[k] / ((1 - V) + V * K[k]);
    vap[k] = s[k] * fv; liq[k] = s[k] - vap[k];
  }
  return { vap, liq, V };
}

// Destilación diferencial (Rayleigh): el vapor sale conforme se forma, hasta que el líquido
// que queda tiene presión de burbuja igual a P. Los no volátiles disueltos (aditivos, polímeros) diluyen.
function rayleigh(s, TK, P, nc = 0) {
  const liq = copy(s), vap = {};
  const ps = {};
  for (const k of VOLATILES) ps[k] = psatMB(SP[k].Tb, TK);
  const dissolved = ['AD', 'OXh', 'VI'];
  // el vapor de arrastre (cantidad fija) baja la presión parcial que tiene que vencer el líquido
  let n0 = 0;
  for (const k of VOLATILES) if (liq[k] > 0) n0 += liq[k] / SP[k].M;
  const Peff = nc > 0 && n0 > 0 ? P * n0 / (n0 + nc) : P;
  for (let it = 0; it < 2000; it++) {
    let n = 0;
    const nk = {};
    for (const k of VOLATILES) if (liq[k] > 1e-12) { nk[k] = liq[k] / SP[k].M; n += nk[k]; }
    let nNV = 0;
    for (const k of dissolved) nNV += (liq[k] || 0) / SP[k].M;
    if (n <= 0) break;
    const Pb = Object.keys(nk).reduce((a, k) => a + nk[k] / (n + nNV) * ps[k], 0);
    if (Pb <= Peff) break;
    const dN = Math.min(0.004 * n, n * (1 - Peff / Pb) + 1e-9);
    for (const k in nk) {
      const y = nk[k] * ps[k] / (n + nNV) / Pb;
      const dm = Math.min(liq[k], y * dN * SP[k].M);
      liq[k] -= dm; vap[k] = (vap[k] || 0) + dm;
    }
  }
  return { vap, liq };
}

// Distribución lognormal de tamaños (fracción de masa por clase) para la sedimentación
function lognormalBins(d50, sg, n = 60) {
  const out = [], ls = Math.log(sg);
  const lo = Math.log(d50) - 3.5 * ls, hi = Math.log(d50) + 3.5 * ls, step = (hi - lo) / n;
  let tot = 0;
  for (let i = 0; i < n; i++) { const x = lo + (i + 0.5) * step, w = Math.exp(-0.5 * Math.pow((x - Math.log(d50)) / ls, 2)); out.push([Math.exp(x), w]); tot += w; }
  return out.map(([d, w]) => [d, w / tot]);
}
function settledFraction(bins, drho, mu, t, H) {
  if (drho <= 0) return 0;
  return bins.reduce((a, [d, w]) => a + w * Math.min(1, G * drho * d * d / (18 * mu) * t / H), 0);
}

// ---------- Etapas ----------
// 1. Sedimentación: Stokes sobre gotas de agua libre y partículas gruesas
function sedimentacion(s, c) {
  const T = c.Ts + 273.15, t = c.ts * 3600, H = c.H;
  const nu = walther(c.v40, c.v100, T) * 1e-6;
  const rhoO = 885 - 0.65 * (T - 288), rhoW = 1000 - 0.0036 * Math.pow(T - 277, 2);
  const mu = nu * rhoO;
  const fW = settledFraction(lognormalBins(60e-6, 2.5), rhoW - rhoO, mu, t, H);
  const fP = settledFraction(lognormalBins(12e-6, 2.2), 3500 - rhoO, mu, t, H);
  const out = copy(s);
  const rem = { W: s.W * FREE_WATER * fW, PW: s.PW * fP };
  out.W -= rem.W; out.PW -= rem.PW;
  // el agua drenada arrastra aceite (≈ 5 % de lo drenado)
  const drag = 0.05 * (rem.W + rem.PW), oil = oilMass(out);
  const waste = copy(rem);
  for (const k of [...BASE, 'FG', 'FD']) { const x = drag * out[k] / oil; out[k] -= x; waste[k] = (waste[k] || 0) + x; }
  const E = s.W ? (oilMass(s) * CP_OIL + s.W * 4186) * Math.max(0, T - c.Tamb) : 0;
  return { out, waste: { 'Agua aceitosa': waste }, E, time: E / c.Ph + t, info: { fW, fP, mu, nu: nu * 1e6 } };
}

// 2. Deshidratación a presión atmosférica: el vapor de agua arrastra parte del combustible
function deshidratacion(s, c) {
  const T = c.Td + 273.15;
  const fwat = clamp(psatWater(T) / PATM, 0, 1);
  const out = copy(s);
  const wOut = s.W * (T >= 373.15 ? 1 : fwat);
  out.W = s.W - wOut;
  const fl = flash(out, T, PATM, wOut / SP.W.M);
  const fuel = fl.vap;
  for (const k in fuel) out[k] -= fuel[k];
  const E = oilMass(s) * CP_OIL * Math.max(0, T - (c.Ts + 273.15)) + wOut * LAT_W + sum(fuel) * LAT_HC;
  return { out, products: { 'Combustible ligero': fuel }, waste: { 'Agua condensada': { W: wOut } }, E, time: E / c.Ph + 1800, info: { wOut } };
}

// 3. Tratamiento químico
const ETA_SOLV = { AD: 0.55, VI: 0.75, OXh: 0.70, OXv: 0.35, DV: 0.35, SO: 0.90, PW: 0.95 }; // a S = 4, KOH = 2 g/kg, 4 h
const ETA_ACID = { AD: 0.90, VI: 0.80, OXh: 0.85, OXv: 0.85, DV: 0.85, SO: 0.95, PW: 0.95 };
const ETA_DAP = { VI: 0.10, OXh: 0.10, OXv: 0.05, DV: 0.05, SO: 0.50, PW: 0.80 };
function solventFactor(S, koh, th) {
  const f = (S, k, t) => (1 - Math.exp(-S / 1.5)) * (0.6 + 0.4 * k / (k + 1)) * (1 - Math.exp(-t / 1.5));
  return Math.min(1.15, f(S, koh, th) / f(4, 2, 4));
}
function metalsMass(s) { return sum(s, ['AD']) * (METALS.AD.Ca + METALS.AD.Zn + METALS.AD.P) + (s.PW || 0) * (METALS.PW.Fe + METALS.PW.Pb + METALS.PW.Si); }

function tratamiento(s, c) {
  const out = copy(s), sludge = {};
  const oil0 = oilMass(s);
  let eta = {}, E = 0, time = 0, reagent = 0, holdup = 0.6, label = 'Lodo';
  if (c.ruta === 'solvente') {
    const F = solventFactor(c.S, c.koh, c.t3);
    for (const k in ETA_SOLV) eta[k] = Math.min(0.99, ETA_SOLV[k] * F);
    reagent = c.koh / 1000 * c.S * oil0;
    const ipa = c.S * oil0, lost = 0.03 * ipa;
    sludge.IPA = lost * 0.5;
    E = ipa * (CP_IPA * 60 + LAT_IPA) + oil0 * CP_OIL * 20;
    time = 1800 + c.t3 * 3600 + E / c.Ph;
    out.IPA = 0;
    eta._ipa = { used: ipa, lost };
  } else if (c.ruta === 'dap') {
    const metals = metalsMass(s) / oil0;
    const r = (c.dap / 100) / (2.5 * metals);
    const k = 0.05 * Math.exp(-60e3 / R * (1 / (c.T3 + 273.15) - 1 / 413.15));
    eta = Object.assign({ AD: 0.75 * (1 - Math.exp(-2 * r)) * (1 - Math.exp(-k * c.t3min)) }, ETA_DAP);
    reagent = c.dap / 100 * oil0;
    const water = 1.5 * reagent;
    E = oil0 * CP_OIL * Math.max(0, c.T3 + 273.15 - (c.Td + 273.15)) + water * LAT_W;
    time = c.t3min * 60 + 3600 + E / c.Ph;
    holdup = 0.5; label = 'Torta de fosfatos';
  } else if (c.ruta === 'acido') {
    eta = Object.assign({}, ETA_ACID);
    reagent = c.acido / 100 * oil0;
    holdup = 0.8; label = 'Lodo ácido';
    time = 3600 + 12 * 3600;
  }
  let removed = 0;
  for (const k in eta) {
    if (k[0] === '_' || !(s[k] > 0)) continue;
    const x = s[k] * eta[k]; out[k] -= x; sludge[k] = (sludge[k] || 0) + x; removed += x;
  }
  // el lodo retiene aceite base (y el ácido se lleva más)
  const carry = holdup * (removed + reagent);
  const oilB = sum(out, BASE);
  for (const b of BASE) { const x = carry * out[b] / oilB; out[b] -= x; sludge[b] = (sludge[b] || 0) + x; }
  sludge.REA = reagent;
  const waste = c.ruta === 'ninguno' ? {} : { [label]: sludge };
  return { out, waste, E, time, reagent, info: { eta, removed, carry } };
}

// 4. Destilación al vacío: separación de gasóleo y evaporador de película (TFE) con condensación fraccionada
function destilacion(s, c) {
  const Tw = c.Tw + 273.15, P = c.Pv * 100;   // Pv en mbar
  const feed = copy(s);
  // 4a. separación de gasóleo (destilación diferencial con vapor de arrastre)
  const go = rayleigh(feed, c.Tgo + 273.15, c.Pgo * 100, c.steam * oilMass(feed) / SP.W.M);
  const afterGo = go.liq;
  // descomposición de aditivos en la pared caliente: una parte se vuelve destilable (DV)
  const kd = 0.778 * Math.exp(-80e3 / R * (1 / Tw - 1 / 593.15));
  const dec = (afterGo.AD || 0) * (1 - Math.exp(-kd));
  afterGo.AD -= dec; afterGo.DV = (afterGo.DV || 0) + 0.4 * dec;
  const decRes = 0.6 * dec;
  // craqueo térmico del aceite base arriba de ~330 °C
  const kc = 0.01005 * Math.exp(-220e3 / R * (1 / Tw - 1 / 613.15));
  let cracked = 0;
  for (const b of BASE) { const x = afterGo[b] * (1 - Math.exp(-kc)); afterGo[b] -= x; cracked += x; }
  // 4b. TFE: destilación diferencial a la temperatura de pared y al vacío
  const tfe = rayleigh(afterGo, Tw, P);
  const residue = tfe.liq;
  residue.AD = (residue.AD || 0) + decRes;
  const dist = tfe.vap;
  // arrastre de gotas del residuo hacia el destilado
  const eps = 0.003;
  for (const k in residue) { const x = residue[k] * eps; residue[k] -= x; dist[k] = (dist[k] || 0) + x; }
  // 4c. condensador caliente y frío
  const hot = flash(dist, c.Thc + 273.15, P);
  const heavy = hot.liq, light = hot.vap;
  // ensuciamiento del evaporador: lo no volátil que llega, más caliente = peor
  const nvIn = sum(afterGo, ['AD', 'VI', 'SO', 'OXh']) / Math.max(1e-9, oilMass(afterGo));
  const fouling = nvIn * 100 * Math.exp((Tw - 593.15) / 30);
  const mIn = oilMass(s);
  const E = mIn * CP_OIL * Math.max(0, Tw - (c.Td + 273.15)) + (sum(dist) + sum(go.vap)) * LAT_HC;
  const time = mIn / c.feedRate * 3600;
  return {
    out: { heavy, light }, products: { 'Gasóleo (combustible)': go.vap },
    waste: { 'Residuo de fondo': residue, 'Ligeros de craqueo': { FG: cracked } },
    E: E + c.vacuumKW * 1000 * time, time, info: { dec, cracked, fouling, V: tfe.V },
  };
}

// 5. Acabado con arcilla: isoterma de Freundlich para los compuestos polares y filtración
const FREUNDLICH = { K: 75, n: 1.35, dH: 20e3, Tref: 393.15 }; // n de bentonita; K calibrado a re-refinación
function arcilla(s, c) {
  const out = copy(s);
  const oil = oilMass(s);
  if (oil <= 0) return { out, waste: {}, E: 0, time: 0, info: {} };
  const dose = c.clay / 100;
  const K = FREUNDLICH.K * Math.exp(-FREUNDLICH.dH / R * (1 / (c.Tcl + 273.15) - 1 / FREUNDLICH.Tref));
  const polarKeys = ['OXv', 'DV', 'OXh'];
  const C0 = sum(s, polarKeys) / oil;
  // C0 = C + dosis · K · C^(1/n)  → bisección
  let lo = 0, hi = C0;
  for (let i = 0; i < 80; i++) { const m = 0.5 * (lo + hi); if (m + dose * K * Math.pow(m, 1 / FREUNDLICH.n) > C0) hi = m; else lo = m; }
  const approach = 1 - Math.exp(-c.tcl / 10);
  const Ceq = 0.5 * (lo + hi), C = C0 - (C0 - Ceq) * approach;
  const frac = C0 > 0 ? C / C0 : 1;
  const spent = { CL: dose * oil };
  for (const k of polarKeys) { const x = (s[k] || 0) * (1 - frac); out[k] = (out[k] || 0) - x; spent[k] = x; }
  // la filtración quita sólidos arrastrados
  for (const k of ['SO', 'PW', 'AD', 'VI']) { const x = (out[k] || 0) * 0.9; out[k] = (out[k] || 0) - x; spent[k] = (spent[k] || 0) + x; }
  // la arcilla gastada retiene aceite
  const b = sum(out, BASE), carry = Math.min(0.35 * dose * oil, 0.5 * b);
  for (const k of BASE) { const x = b > 0 ? carry * out[k] / b : 0; out[k] -= x; spent[k] = (spent[k] || 0) + x; }
  const E = oil * CP_OIL * Math.max(0, c.Tcl - 40);
  return { out, waste: { 'Arcilla gastada': spent }, E, time: c.tcl * 60 + 3600 + E / c.Ph, info: { C0, C } };
}

// 5b. Hidroacabado: hidrógeno a 30–60 bar y 300–340 °C sobre catalizador NiMo; satura y quita polares
function hidroacabado(s, c) {
  const out = copy(s), waste = {};
  const oil = oilMass(s);
  for (const [k, eta] of [['OXv', 0.97], ['DV', 0.98], ['OXh', 0.95], ['AD', 0.9], ['SO', 0.95], ['PW', 0.95], ['VI', 0.9]]) {
    const x = (s[k] || 0) * eta; out[k] = (out[k] || 0) - x; waste[k] = x;
  }
  // ≈ 1 % del aceite se craquea a ligeros
  const b = sum(out, BASE);
  for (const k of BASE) { const x = 0.01 * out[k]; out[k] -= x; waste.FG = (waste.FG || 0) + x; }
  const E = oil * CP_OIL * 280 * 0.3;  // con intercambio de calor carga/efluente
  return { out, waste: { 'Agua ácida y ligeros del hidroacabado': waste }, E, time: oil / c.feedRate * 3600, info: {} };
}

// ---------- Calidad ----------
function calidad(s) {
  const m = sum(s);
  if (m <= 0) return null;
  const v = blendVisc(s);
  const polar = sum(s, ['OXv', 'DV', 'OXh']) / m;
  const tan = (100 * sum(s, ['OXv', 'OXh']) + 50 * (s.DV || 0)) / m;
  const metals = metalsMass(s) / m;
  const soot = sum(s, ['SO']) / m;
  const color = clamp(0.5 + 1.8 * Math.log10(1 + (polar * 1e6 + 100 * soot * 1e6) / 150), 0.5, 8);
  // punto de inflamación: temperatura a la que la presión de vapor de la mezcla llega a P_fl
  let n = 0;
  const x = {};
  for (const k of VOLATILES) if (s[k] > 0) { x[k] = s[k] / SP[k].M; n += x[k]; }
  const pv = (T) => Object.keys(x).reduce((a, k) => a + x[k] / n * psatMB(SP[k].Tb, T), 0);
  let lo = 250, hi = 700;
  for (let i = 0; i < 60; i++) { const T = 0.5 * (lo + hi); if (pv(T) > P_FLASH) hi = T; else lo = T; }
  const iso = [10, 15, 22, 32, 46, 68, 100, 150, 220, 320, 460, 680].reduce((a, g) => (Math.abs(Math.log(g / v.v40)) < Math.abs(Math.log(a / v.v40)) ? g : a));
  return {
    kg: m, litros: m / 0.87, v40: v.v40, v100: v.v100, isoVG: iso, flash: 0.5 * (lo + hi) - 273.15,
    tan, color, ash_ppm: metals * ASH_FACTOR * 1e6, metals_ppm: metals * 1e6, polar_ppm: polar * 1e6,
  };
}
const P_FLASH = 150; // Pa; calibrado para que un SN-150 dé ≈ 210 °C (copa abierta)

// ---------- Proceso completo ----------
function procesar(c) {
  const feed = feedStream(c.tipo, c.mass);
  const stages = [];
  const waste = {}, products = {};
  const merge = (dst, src) => { for (const k in src || {}) dst[k] = addTo(dst[k] || {}, src[k]); };
  let s = feed;
  const s1 = sedimentacion(s, c); stages.push(['sedimentacion', s1]); merge(waste, s1.waste); s = s1.out;
  const s2 = deshidratacion(s, c); stages.push(['deshidratacion', s2]); merge(waste, s2.waste); merge(products, s2.products); s = s2.out;
  const s3 = tratamiento(s, c); stages.push(['tratamiento', s3]); merge(waste, s3.waste); s = s3.out;
  const s4 = destilacion(s, c); stages.push(['destilacion', s4]); merge(waste, s4.waste); merge(products, s4.products);
  const fin = c.acabado === 'hidro' ? hidroacabado : arcilla;
  const lightCl = fin(s4.out.light, c), heavyCl = fin(s4.out.heavy, c);
  const s5 = {
    out: { light: lightCl.out, heavy: heavyCl.out }, E: lightCl.E + heavyCl.E, time: Math.max(lightCl.time, heavyCl.time),
    waste: {}, info: { light: lightCl.info, heavy: heavyCl.info },
  };
  merge(s5.waste, lightCl.waste); merge(s5.waste, heavyCl.waste);
  stages.push(['arcilla', s5]); merge(waste, s5.waste);
  products['Aceite base ligero'] = s5.out.light;
  products['Aceite base pesado'] = s5.out.heavy;
  const added = { REA: s3.reagent || 0, CL: c.acabado === 'hidro' ? 0 : c.clay / 100 * (oilMass(s4.out.light) + oilMass(s4.out.heavy)), IPA: s3.info.eta._ipa ? s3.info.eta._ipa.lost * 0.5 : 0 };
  const E = stages.reduce((a, [, st]) => a + st.E, 0) / 0.85;
  const time = stages.reduce((a, [, st]) => a + st.time, 0);
  const inTot = c.mass + sum(added), outTot = sum(Object.values(products).map((p) => sum(p))) + sum(Object.values(waste).map((w) => sum(w)));
  return {
    feed, stages, products, waste, added, E, time, closure: outTot / inTot - 1,
    q: { light: calidad(s5.out.light), heavy: calidad(s5.out.heavy), feed: calidad(feed) },
    base_kg: sum(s5.out.light, BASE) + sum(s5.out.heavy, BASE), prod_kg: sum(s5.out.light) + sum(s5.out.heavy), base_in: sum(feed, BASE),
    ipa: s3.info.eta._ipa || null, fouling: s4.info.fouling, info: s4.info,
  };
}

function config(o = {}) {
  return Object.assign({
    tipo: 'taller', mass: 175, Tamb: 298.15, Ph: 15000, v40: 95, v100: 13.5,
    Ts: 60, ts: 12, H: 0.8,
    Td: 150,
    ruta: 'solvente', S: 3, koh: 2, t3: 4, dap: 2, T3: 140, t3min: 60, acido: 6,
    Tgo: 265, Pgo: 20, steam: 0.02, Tw: 320, Pv: 2, Thc: 235, feedRate: 25, vacuumKW: 1.1,
    acabado: 'arcilla', clay: 6, Tcl: 140, tcl: 30,
  }, o);
}
// MODEL-END
if (typeof module !== 'undefined') module.exports = { procesar, config, calidad, feedStream, psatMB, walther, blendVisc, flash, SP, BASE };
