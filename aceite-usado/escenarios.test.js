// Pruebas del modelo: node escenarios.test.js
const M = require('./model.js');
const sum = (o) => Object.values(o).reduce((a, b) => a + b, 0);
let fallas = 0;
const ok = (cond, msg) => { console.log(`${cond ? '✓' : '✗'} ${msg}`); if (!cond) fallas++; };
const run = (o) => M.procesar(M.config(o));

// Propiedades físicas
ok(Math.abs(M.psatMB(400, 300) / 2100 - 1) < 0.05, 'presión de vapor del octano a 27 °C ≈ 2.1 kPa (Maxwell–Bonnell)');
ok(Math.abs(M.walther(95, 13.5, 313.15) - 95) < 0.01 && Math.abs(M.walther(95, 13.5, 373.15) - 13.5) < 0.01, 'Walther reproduce los dos puntos de viscosidad');
ok(M.walther(95, 13.5, 333.15) < 95 && M.walther(95, 13.5, 333.15) > 13.5, 'viscosidad a 60 °C entre la de 40 y la de 100 °C');

// Balance de masa en todas las rutas y condiciones extremas
const casos = [{}, { ruta: 'dap' }, { ruta: 'acido' }, { ruta: 'ninguno' }, { clay: 0 }, { clay: 10 }, { Tw: 360 }, { Ts: 25, ts: 1 },
  { tipo: 'diesel' }, { tipo: 'agua' }, { tipo: 'gasolina', ruta: 'dap', dap: 0.2 }, { S: 6, koh: 5 }, { Pv: 10 }, { Thc: 300 }];
const res = casos.map(run);
ok(res.every((r) => Math.abs(r.closure) < 1e-9), `balance de masa cierra en ${casos.length} casos`);
ok(res.every((r) => Object.values(r.products).every((p) => Object.values(p).every((x) => Number.isFinite(x) && x >= -1e-12))), 'ninguna corriente con masa negativa o NaN');

// Tendencias que la física y la literatura exigen
const [base, dap, acido, nada] = res;
ok(acido.q.heavy.tan < base.q.heavy.tan && base.q.heavy.tan < nada.q.heavy.tan, 'TAN: ácido < solvente < sin tratamiento');
ok(sum(acido.waste['Lodo ácido']) > 1.5 * sum(base.waste['Lodo']), 'la ruta ácida genera bastante más lodo, y además corrosivo');
ok(base.E > 2 * nada.E, 'recuperar el solvente cuesta más del doble de energía');
ok(nada.fouling > base.fouling, 'sin tratamiento ensucia más el evaporador');
ok(run({ clay: 8 }).q.heavy.color < run({ clay: 2 }).q.heavy.color, 'más arcilla, mejor color');
ok(run({ Ts: 80 }).stages[0][1].info.fW > run({ Ts: 25 }).stages[0][1].info.fW, 'sedimentar en caliente quita más agua (Stokes)');
ok(run({ Tw: 340 }).base_kg > run({ Tw: 300 }).base_kg, 'más temperatura de pared, más destilado');
ok(run({ Tw: 360 }).waste['Ligeros de craqueo'].FG > 5 * base.waste['Ligeros de craqueo'].FG, 'arriba de 340 °C se craquea el aceite');
ok(run({ Pv: 10 }).base_kg < base.base_kg, 'peor vacío, menos destilado');
ok(base.q.light.v40 < base.q.heavy.v40, 'el corte ligero es menos viscoso que el pesado');
ok(base.base_kg / 175 > 0.55 && base.base_kg / 175 < 0.85, `rendimiento de aceite base ${(100 * base.base_kg / 175).toFixed(0)} % de la carga (literatura: 70–90 % de destilado)`);
ok(base.q.light.flash > 170 && base.q.heavy.flash > 210, `punto de inflamación ${base.q.light.flash.toFixed(0)} / ${base.q.heavy.flash.toFixed(0)} °C`);
ok(dap.stages[2][1].info.eta.AD > 0.6, `fosfato diamónico al 2 % quita ${(100 * dap.stages[2][1].info.eta.AD).toFixed(0)} % de la ceniza (patente: 0.5 → 0.15 %)`);

console.log(fallas ? `\n${fallas} falla(s)` : '\nTodo en verde');
process.exit(fallas ? 1 : 0);
