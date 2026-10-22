// MODEL-START
// Modelo de lumps para pirólisis semi-batch de plásticos. Unidades SI (kg, K, Pa, mol, J, s).
const R = 8.314, PATM = 101325;
const RHO = 750;            // densidad del fundido, kg/m3
const CP_POLY = 2400, CP_LIQ = 2500, CP_CHAR = 1000, CP_STEEL = 500; // J/kg·K
const K_EV = 0.15;          // constante de evaporación, 1/s
const KV = 2e-5;            // válvula de contrapresión, mol/(s·Pa)
const KR = 1e-3;            // válvula de alivio (PSV), mol/(s·Pa)
const P_RELIEF = 6e5;       // disparo PSV, Pa abs
const ETA_R = 0.9;          // eficiencia del deflegmador
const DH_SEC = 0.3e6;       // calor de craqueo secundario, J/kg
const LHV_GAS = 46e6, ETA_B = 0.75; // gas C1–C4 y eficiencia del quemador
const KP = 2500, KI = 8;    // control PI del calentador

const POLY = {
  HDPE: { name: 'PEAD', A: 1.0e16, Ea: 268e3, s: { W: .55, D: .22, G: .13, Gs: .08, C: .02 }, Tm: 403, dHm: 190e3, dHr: 1.05e6 },
  LDPE: { name: 'PEBD', A: 2.2e14, Ea: 240e3, s: { W: .45, D: .27, G: .16, Gs: .10, C: .02 }, Tm: 383, dHm: 120e3, dHr: 0.95e6 },
  PP:   { name: 'PP',   A: 1.9e13, Ea: 220e3, s: { W: .30, D: .32, G: .25, Gs: .11, C: .02 }, Tm: 438, dHm: 90e3,  dHr: 0.85e6 },
  PS:   { name: 'PS',   A: 3.0e12, Ea: 200e3, s: { W: .10, D: .15, G: .65, Gs: .03, C: .07 }, Tm: 0,   dHm: 0,     dHr: 0.65e6 },
};
// Lumps: W ceras C23+, D diésel C13–C22, G gasolina C5–C12, Gs gas C1–C4
const LUMP = {
  W:  { M: 0.45, Tb: 780 },
  D:  { M: 0.23, Tb: 560 },
  G:  { M: 0.10, Tb: 400 },
  Gs: { M: 0.03 },
};
for (const k of ['W', 'D', 'G']) LUMP[k].dHv = 88 * LUMP[k].Tb / LUMP[k].M; // Trouton, J/kg
const SEC = {
  W: { A: 2e11,   Ea: 180e3, to: { D: .75, G: .20, Gs: .05 } },
  D: { A: 1e12,   Ea: 200e3, to: { G: .80, Gs: .20 } },
  G: { A: 1.2e12, Ea: 210e3, to: { Gs: 1 } },
};
const COKE = { A: 1e8, Ea: 170e3 };
const CAT = {
  none: { name: 'Sin catalizador', beta: 0, smax: 0,   to: null },
  FCC:  { name: 'FCC de equilibrio', beta: 2, smax: .60, to: { D: .45, G: .45, Gs: .07, C: .03 } },
  HY:   { name: 'Zeolita HY',      beta: 3, smax: .75, to: { D: .30, G: .55, Gs: .10, C: .05 } },
  ZSM5: { name: 'ZSM-5',           beta: 4, smax: .85, to: { G: .70, Gs: .25, C: .05 } },
};

function psat(Tb, T) { return PATM * Math.exp(Math.min(40, (88 / R) * (1 - Tb / T))); }
function clamp(x, a, b) { return x < a ? a : x > b ? b : x; }

function makeState(c) {
  const mP = {};
  let tot = 0;
  for (const k in c.mix) tot += c.mix[k];
  for (const k in c.mix) mP[k] = tot > 0 ? c.mass * c.mix[k] / tot : 0;
  const s = {
    t: 0, T: c.Tamb, P: PATM, I: 0, Q: 0, relief: false, done: false, tau: 0,
    mP, mass0: c.mass, L: { W: 0, D: 0, G: 0 }, V: { W: 0, D: 0, G: 0, Gs: 0 },
    nN2: 0, char: 0, tank: { G: 0, D: 0, W: 0 }, gasFlare: 0, gasBurn: 0, gasLossG: 0,
    Eext: 0, Egas: 0, cum: { prim: 0, evap: 0, refl: 0, out: { W: 0, D: 0, G: 0, Gs: 0 } }, tDone: 0,
  };
  const Vh = Math.max(0.01, c.Vr - c.mass / RHO);
  s.nN2 = PATM * Vh / (R * c.Tamb); // espacio de cabeza purgado con N2 a 1 atm
  return s;
}

function step(s, c, dt) {
  const T = s.T, RT = R * T;
  let mPtot = 0;
  for (const j in s.mP) mPtot += s.mP[j];
  const Ltot = s.L.W + s.L.D + s.L.G;
  const Vh = Math.max(0.01, c.Vr - (mPtot + Ltot + s.char) / RHO);
  const cat = CAT[c.cat], phi = c.catLoad;
  const mult = 1 + cat.beta * phi / 0.1;
  const sig = cat.smax * phi / (phi + 0.05);

  // 1. Craqueo primario del polímero (Arrhenius de primer orden)
  let Qr = 0;
  for (const j in s.mP) {
    const p = POLY[j], m = s.mP[j];
    if (m <= 0) continue;
    const r = Math.min(p.A * Math.exp(-p.Ea / RT) * mult * m, m / dt);
    s.mP[j] = m - r * dt;
    const x = r * dt, sh = sig * p.s.W;
    s.L.W += x * (p.s.W - sh); s.L.D += x * p.s.D; s.L.G += x * p.s.G;
    s.V.Gs += x * p.s.Gs; s.char += x * p.s.C;
    if (cat.to) {
      const y = x * sh;
      s.L.D += y * (cat.to.D || 0); s.L.G += y * (cat.to.G || 0);
      s.V.Gs += y * (cat.to.Gs || 0); s.char += y * (cat.to.C || 0);
    }
    Qr += r * p.dHr;
    s.cum.prim += x;
  }

  // 2. Craqueo secundario en líquido y vapor
  let Qs = 0;
  for (const i of ['W', 'D', 'G']) {
    const q = SEC[i], k = q.A * Math.exp(-q.Ea / RT) * mult;
    const rl = Math.min(k * s.L[i], s.L[i] / dt), rv = Math.min(0.5 * k * s.V[i], s.V[i] / dt);
    s.L[i] -= rl * dt; s.V[i] -= rv * dt;
    for (const o in q.to) {
      const f = q.to[o];
      if (o === 'Gs') s.V.Gs += (rl + rv) * f * dt;
      else { s.L[o] += rl * f * dt; s.V[o] += rv * f * dt; }
    }
    Qs += (rl + rv) * DH_SEC;
  }
  const kc = COKE.A * Math.exp(-COKE.Ea / RT);
  for (const i of ['W', 'D']) {
    const r = Math.min(kc * s.L[i], s.L[i] / dt);
    s.L[i] -= r * dt; s.char += r * dt;
  }

  // 3. Evaporación del líquido, impulsada por Psat/P
  let Qv = 0;
  for (const i of ['W', 'D', 'G']) {
    const f = Math.min(1, psat(LUMP[i].Tb, T) / s.P);
    const e = Math.min(K_EV * f * s.L[i], s.L[i] / dt);
    s.L[i] -= e * dt; s.V[i] += e * dt;
    Qv += e * LUMP[i].dHv;
    s.cum.evap += e * dt;
  }

  // 4. Purga de N2
  s.nN2 += c.n2 * dt;

  // 5. Presión (gas ideal) y salida por válvula de contrapresión, implícito
  const N0 = s.nN2 + s.V.W / LUMP.W.M + s.V.D / LUMP.D.M + s.V.G / LUMP.G.M + s.V.Gs / LUMP.Gs.M;
  const cc = RT / Vh;
  let N1 = N0;
  if (cc * N0 > c.Pset) {
    N1 = (N0 + dt * KV * c.Pset) / (1 + dt * KV * cc);
    if (cc * N1 > P_RELIEF) N1 = (N0 + dt * (KV * c.Pset + KR * P_RELIEF)) / (1 + dt * (KV + KR) * cc);
  }
  s.relief = cc * N1 > P_RELIEF * 0.98;
  const frac = N0 > 0 ? (N0 - N1) / N0 : 0;
  const out = {};
  for (const i of ['W', 'D', 'G', 'Gs']) { out[i] = s.V[i] * frac; s.V[i] -= out[i]; }
  const outN2 = s.nN2 * frac;
  s.nN2 -= outN2;
  s.P = cc * N1;
  const nOut = (N0 - N1) / dt;
  s.tau = nOut > 1e-6 ? N1 / nOut : Infinity;

  // 6. Deflegmador: regresa al reactor lo que condensa a Td
  if (c.reflux) {
    const Td = Math.min(c.Tref, T);
    for (const i of ['W', 'D', 'G']) {
      const b = out[i] * ETA_R * Math.max(0, 1 - psat(LUMP[i].Tb, Td) / s.P);
      out[i] -= b; s.L[i] += b; s.cum.refl += b;
    }
  }
  for (const i of ['W', 'D', 'G', 'Gs']) s.cum.out[i] += out[i];

  // 7. Condensador: el gas no condensable arrastra gasolina a saturación
  const PsG = psat(LUMP.G.Tb, c.Tc);
  let lossG = 0;
  if (PsG < s.P) {
    const nNC = outN2 + out.Gs / LUMP.Gs.M;
    lossG = Math.min(out.G, nNC * PsG / (s.P - PsG) * LUMP.G.M);
  }
  s.tank.W += out.W; s.tank.D += out.D; s.tank.G += out.G - lossG;
  s.gasLossG += lossG;
  const gasM = out.Gs + lossG;

  // 8. Calentador con control PI y gas recirculado al quemador
  const e = c.Tsp - T;
  if (Math.abs(e) < 25) s.I = clamp(s.I + KI * e * dt, 0, c.Pmax);
  const Q = clamp(KP * e + s.I, 0, c.Pmax);
  let Qgas = 0, burn = 0;
  if (c.recirc && gasM > 0) {
    Qgas = Math.min(Q, gasM / dt * LHV_GAS * ETA_B);
    burn = Qgas * dt / (LHV_GAS * ETA_B);
  }
  s.gasBurn += burn; s.gasFlare += gasM - burn;
  s.Eext += (Q - Qgas) * dt; s.Egas += Qgas * dt;
  s.Q = Q; s.Qgas = Qgas;

  // 9. Balance de energía del reactor
  let C = c.mSteel * CP_STEEL + Ltot * CP_LIQ + s.char * CP_CHAR;
  for (const j in s.mP) {
    const p = POLY[j];
    C += s.mP[j] * CP_POLY;
    if (p.dHm > 0) { const sg = 6, z = (T - p.Tm) / sg; C += s.mP[j] * p.dHm * Math.exp(-0.5 * z * z) / (sg * 2.5066); }
  }
  s.Qloss = c.UA * (T - c.Tamb);
  s.Qrxn = Qr + Qs + Qv;
  s.T = T + (Q - Qr - Qs - Qv - s.Qloss) / C * dt;
  s.t += dt;

  const left = mPtot + Ltot;
  if (!s.done && s.t > 600 && left < 0.003 * s.mass0) { s.done = true; s.tDone = s.t; }
}

function summary(s) {
  let mP = 0;
  for (const j in s.mP) mP += s.mP[j];
  const L = s.L.W + s.L.D + s.L.G, V = s.V.W + s.V.D + s.V.G + s.V.Gs;
  const gas = s.gasFlare + s.gasBurn;
  const acc = s.tank.G + s.tank.D + s.tank.W + gas + s.char + mP + L + V;
  return {
    G: s.tank.G, D: s.tank.D, W: s.tank.W, gas, char: s.char, inside: mP + L + V,
    conv: 1 - mP / s.mass0, closure: acc / s.mass0 - 1,
  };
}
// MODEL-END
if (typeof module !== 'undefined') module.exports = { makeState, step, summary, POLY, CAT, LUMP, PATM };
