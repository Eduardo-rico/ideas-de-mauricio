// Pruebas del modelo del búnker: node escenarios.test.js
const M = require('./model.js');
let fallas = 0;
const ok = (cond, msg) => { console.log(`${cond ? '✓' : '✗'} ${msg}`); if (!cond) fallas++; };
const rel = (a, b) => Math.abs(a - b) / Math.max(1e-9, Math.abs(b));
const run = (o) => M.simular(o);

// Datos fisiológicos contra NASA BVAD y contra el cálculo a mano
const n = M.necesidades(M.config());
const h = M.necesidades(M.config({ perros: 0, personas: 1, kcalPersona: 2822 }));
ok(rel(h.o2kgDia, 0.835) < 0.03, `O₂ de una persona a 2 822 kcal/día: ${h.o2kgDia.toFixed(3)} kg (NASA BVAD: 0.835)`);
ok(rel(h.co2kgDia, 0.998) < 0.03, `CO₂ de una persona: ${h.co2kgDia.toFixed(3)} kg (NASA BVAD: 0.998)`);
ok(rel(n.co2kgDia / n.o2kgDia, 0.87 * 44 / 32) < 1e-9, 'CO₂/O₂ en masa = RQ × 44/32');
ok(rel(n.comidaKg, 2200 * 5 * 1095 / 3500) < 1e-9, `comida para 3 años: ${n.comidaKg.toFixed(0)} kg de alimento seco`);
ok(n.ventPara1000ppm > 150 && n.ventPara1000ppm < 400, `ventilación para 1 000 ppm de CO₂: ${n.ventPara1000ppm.toFixed(0)} m³/h`);

// Blindaje: 1 m de tierra + 30 cm de concreto limitado por la entrada
ok(M.shieldPF(M.config()) === 1000, 'factor de protección limitado por una entrada con dos vueltas = 1 000');
ok(M.shieldPF(M.config({ tierra: 0.091, concreto: 0, vueltas: 3 })) === 2, 'un espesor de medio valor de tierra = factor 2');

// Balances en el caso base y en casos extremos
const casos = [{}, { escenario: '5Tg' }, { sellarDias: 14, calSodada: 50 }, { paneles: 0, generadorKW: 0 }, { aguaL: 2000, techo: 0 }, { hidroArea: 0, aeroArea: 0, algasL: 0, acuarioL: 0, peces: 0 }, { dias: 30 }];
for (const o of casos) {
  const r = run(o), t = r.tot, e = r.end, s0 = r.s0, cb = r.c.bateriaKWh;
  const eb = rel(t.pv + t.gen + t.dis, t.load + t.ch + t.lossDis);
  const soc = Math.abs((e.soc - s0.soc) - (0.95 * t.ch - t.dis));
  const agua = Math.abs((e.agua - s0.agua) - (t.aguaIn - t.aguaOut - t.aguaRebose + t.aguaFalta));
  const o2 = Math.abs((e.o2 - s0.o2) - (t.o2Src + t.o2Vent + t.o2Bottle)) / r.molAir;
  const co2 = Math.abs((e.co2 - s0.co2) - (t.co2Src + t.co2Vent - t.co2Scrub - t.co2Aq)) / r.molAir;
  const aq = Math.abs((e.co2aq - s0.co2aq) - t.co2Aq);
  ok(eb < 1e-9 && soc < 1e-6 * Math.max(1, cb) && agua < 1e-6 && o2 < 1e-9 && co2 < 1e-9 && aq < 1e-9, `balances de energía, batería, agua, O₂ y CO₂ cierran: ${JSON.stringify(o)}`);
}

// Tendencias físicas
const base = run({});
const sellado = run({ sellarDias: 14, calSodada: 0 });
ok(Math.max(...sellado.days.slice(0, 14).map((d) => d.co2max)) > 0.03, 'sellado 14 días sin cal sodada: el CO₂ pasa de 3 %');
ok(base.days.slice(0, 1095).every((d) => d.co2max < 0.005), 'con ventilación filtrada el CO₂ se queda abajo de 5 000 ppm los 3 años');
const sinPlantas = run({ hidroArea: 0, aeroArea: 0, algasL: 0 });
const o2Bio = base.days[400].o2Plant + base.days[400].o2Alg;
ok(o2Bio / base.days[400].o2Met < 0.25, `plantas y algas dan ${(100 * o2Bio / base.days[400].o2Met).toFixed(0)} % del O₂ que se respira (el resto lo da la ventilación)`);
ok(base.days[60].o2Fish > 0, 'los peces consumen oxígeno');
ok(run({ escenario: '150Tg' }).days[200].luz < run({ escenario: '5Tg' }).days[200].luz, 'más hollín, menos sol');
ok(base.days[200].Tout < 18, `a los 200 días afuera hace ${base.days[200].Tout.toFixed(1)} °C`);
ok(run({ paneles: 40 }).tot.kcalProd > base.tot.kcalProd, 'más paneles, más luz para cultivos, más comida');
ok(base.days[1094].dosis < 5, `dosis acumulada dentro en 3 años: ${base.days[1094].dosis.toFixed(2)} rem`);
ok(run({ vueltas: 0 }).days[30].dosis > 10 * base.days[30].dosis, 'entrada recta: mucha más dosis');
ok(run({ techo: 0, reciclaGris: 0, deshum: 0 }).firsts.agua !== undefined, 'sin lluvia ni reciclaje el agua se acaba');
const d7 = base.days[7].rateOut, d49 = base.days[49].rateOut;
ok(rel(d49 / d7, Math.pow(49 / 7, -1.2)) < 0.05, 'regla 7:10: siete veces más tiempo, una décima de la radiación');

// Pecera: el agua absorbe CO2 sólo hasta el equilibrio de Henry
const aq = run({ acuarioL: 3000 }), d30 = aq.days[30];
const gAbs = (d30.co2aqMol - aq.s0.co2aq) * 44;
ok(gAbs < 50, `3 000 L de pecera guardan sólo ${gAbs.toFixed(0)} g de CO₂ en total, contra ${(aq.co2Met * 24 * 44 / 1000).toFixed(1)} kg exhalados al día`);
// Algas dentro de la pecera: rinden menos y respiran de noche
const sep = run({}), dentro = run({ algasEnPecera: true });
ok(dentro.days[400].o2Alg < 0.5 * sep.days[400].o2Alg, 'algas dentro de la pecera dan menos de la mitad del O₂ que en su fotobiorreactor');
// Alimento de peces: al acabarse se cosechan
const pocos = run({ alimentoPeces: 20 });
ok(pocos.firsts['alimento de peces'] !== undefined && pocos.days[pocos.firsts['alimento de peces'] + 1].peces === 0, 'sin alimento, la tilapia se cosecha y se come');
// Clima: mínimas de enero cerca de 7 °C sin guerra y heladas con 150 Tg
const normal = run({ escenario: '5Tg', dias: 30 });
ok(Math.abs(normal.days[10].Tmin - 7) < 1.5, `mínima de enero sin invierno nuclear: ${normal.days[10].Tmin.toFixed(1)} °C (SMN: ≈ 7)`);
ok(base.days.slice(365, 730).filter((d) => d.Tmin < 0).length > 30, 'con 150 Tg hay más de un mes de noches bajo cero en el año 2');

console.log(fallas ? `\n${fallas} falla(s)` : '\nTodo en verde');
process.exit(fallas ? 1 : 0);
