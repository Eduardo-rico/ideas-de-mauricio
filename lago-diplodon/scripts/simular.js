// Corre el modelo sin navegador, usando exactamente el mismo código que la página.
// Uso: node scripts/simular.js            (valores por defecto)
//      node scripts/simular.js dose=600 N0=100 wait=30 prod=lmb years=8
"use strict";
const fs = require("fs");
const path = require("path");
const html = fs.readFileSync(path.join(__dirname, "..", "modelo-lago.html"), "utf8");
const start = html.indexOf("/* =================== PRODUCTS & PARAMS");
const end = html.indexOf("/* =================== CONTROLS");
if (start < 0 || end < 0) throw new Error("No encontré el bloque del modelo en modelo-lago.html");
global.getComputedStyle = () => ({ getPropertyValue: () => "" });
global.document = { documentElement: {} };
const api = new Function(html.slice(start, end) + "\nreturn {P, PRODUCTS, simulate, tsiChl, tsiClass, secchi};")();
const { P, PRODUCTS, simulate, tsiChl, tsiClass } = api;

for (const arg of process.argv.slice(2)) {
  const [k, v] = arg.split("=");
  if (!(k in P)) { console.error(`Parámetro desconocido: ${k}`); process.exit(1); }
  if (k === "prod") Object.assign(P, PRODUCTS[v], { prod: v });
  else P[k] = isNaN(+v) ? v : +v;
}

const fmt = (v) => v.toFixed(1).padStart(6);
console.log(`Producto ${P.prod} · dosis ${P.dose} g/m² · Diplodon ${P.N0} ind/m² · espera ${P.wait} d · carga −${P.red} % · ${P.years} años\n`);
console.log("Clorofila a de verano (µg/L) por año:");
for (const [name, f, m] of [["Sin tratamiento", 0, 0], ["Solo floculante", 1, 0], ["Solo Diplodon", 0, 1], ["Floculante + Diplodon", 1, 1]]) {
  const r = simulate(P, !!f, !!m, true);
  const yrs = [];
  for (let y = 0; y < P.years; y++) {
    let c = 0, n = 0;
    for (let d = y * 365 + 91; d < y * 365 + 212; d++) { c += r.R.A[d] * P.kappa; n++; }
    yrs.push(fmt(c / n));
  }
  const last = r.chlSummer;
  console.log(`${name.padEnd(22)}${yrs.join("")}   → TSI ${tsiChl(last).toFixed(0)} (${tsiClass(last).name})` + (m ? ` · almejas vivas ${r.final.N.toFixed(1)}/m²` : ""));
}
