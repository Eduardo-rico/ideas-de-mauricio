// MODEL-START
// Búnker de soporte de vida para invierno nuclear, Celaya, Gto. Paso de una hora.
// Unidades internas: kg, L, mol, kWh, kcal, °C, horas. Cada componente es un bloque del paso horario.

const KCAL_PER_L_O2 = 4.83;      // kcal por litro de O2 consumido (equivalente calórico)
const KH_CO2 = 0.039;            // mol/(L·atm): solubilidad del CO2 en agua a ~20 °C (Henry)
const RQ = 0.87;                 // cociente respiratorio (NASA BVAD)
const MOL_PER_L_STP = 1 / 22.414;
const P_ALT = 81.8;              // kPa a 1 767 m (Celaya)
const T_REF = 293.15;
const R_GAS = 8.314;

// Clima normal de Celaya (climate-data.org, aproximado mes a mes; media anual 18.3 °C, 689 mm)
const T_NORMAL = [14.7, 16.2, 18.6, 20.9, 22.1, 21.6, 20.1, 20.0, 19.6, 18.2, 16.3, 15.0];
const RAIN_MM = [12, 6, 7, 12, 35, 128, 148, 138, 120, 52, 12, 4];
// Oscilación diaria (máx − mín): ~16 °C en secas y ~12 °C en lluvias; mínima de enero ≈ 7 °C (normales SMN 1991–2020)
const DTR = [15.5, 16, 16, 16, 15, 12.5, 12, 12, 12, 13.5, 15, 15.5];
// Producción fotovoltaica normal, kWh por kWp por día (ProfileSolar, por estación)
const PV_YIELD = [6.04, 6.04, 7.97, 7.97, 7.97, 6.32, 6.32, 6.32, 5.81, 5.81, 5.81, 6.04];

// Escenarios de guerra: hollín en la estratosfera (Robock 2007; Coupe 2019; Xia 2022)
const SCEN = {
  '5Tg':   { name: 'Regional (5 Tg de hollín)', dT: 1.5, light: 0.10, rain: 0.08 },
  '47Tg':  { name: 'Grande (47 Tg)', dT: 5.5, light: 0.40, rain: 0.25 },
  '150Tg': { name: 'Total EUA–Rusia (150 Tg)', dT: 10, light: 0.70, rain: 0.45 },
};
const SOOT_EFOLD_D = 4.6 * 365; // vida media e del hollín, días (Robock 2007)
const SOOT_RISE_D = 20;
const TEMP_LAG_D = 90;
const CTH = 12;                  // kWh/K: masa térmica interior (concreto y contenido), calibrado

// Cultivos: eficiencia del uso de la luz (NASA BPC, Wheeler 2008), g de materia seca por mol de luz
const CROPS = {
  // vitC: mg por g de materia seca comestible (lechuga 9 mg/100 g fresco al 5 % MS; papa 20 mg/100 g al 21 % MS)
  lechuga: { name: 'Lechuga y hojas', lueTot: 0.46, lueEd: 0.42, kcal: 2.9, cycle: 30, prot: 0.25, vitC: 1.8 },
  papa:    { name: 'Papa', lueTot: 0.64, lueEd: 0.44, kcal: 3.6, cycle: 90, prot: 0.09, vitC: 0.95 },
  trigo:   { name: 'Trigo', lueTot: 0.59, lueEd: 0.17, kcal: 3.4, cycle: 80, prot: 0.13, vitC: 0 },
  frijol:  { name: 'Frijol de soya', lueTot: 0.43, lueEd: 0.16, kcal: 4.2, cycle: 90, prot: 0.36, vitC: 0.2 },
};
const O2_PER_G_BIOMASS = 32 / 30;   // CH2O: 1 g de biomasa libera 1.07 g de O2
const CO2_PER_G_BIOMASS = 44 / 30;
// Algas: espirulina (comestible, 30–35 °C, pH 9.5–11 con ~16 g/L de bicarbonato) o chlorella (25–30 °C, pH neutro)
const ALGAS = {
  espirulina: { name: 'Espirulina', tOpt: 32, tMin: 20, kcal: 2.9, prot: 0.6, enPecera: false },
  chlorella:  { name: 'Chlorella', tOpt: 28, tMin: 15, kcal: 3.0, prot: 0.5, enPecera: true },
};
const TRANSP_L_PER_G = 0.25;        // agua transpirada por g de biomasa seca (≈ 4 g/kg de eficiencia)

const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);

function config(o = {}) {
  return Object.assign({
    dias: 1095, personas: 5, kcalPersona: 2200, perros: 4, pesoPerro: 20,
    escenario: '150Tg', tasaH1: 100, llegadaH: 3,
    tierra: 1.0, concreto: 0.3, vueltas: 2,
    area: 130, altura: 2.6,
    vent: 120, ventMax: 600, ventW: 0.3, sellarDias: 0, calSodada: 100, recupCalor: 0.6,
    o2kg: 0, // oxígeno embotellado de reserva
    hidroArea: 10, hidroCultivo: 'lechuga', hidroPPFD: 250,
    aeroArea: 10, aeroCultivo: 'papa', aeroPPFD: 400, fotoperiodo: 16, ledEff: 2.7,
    algasL: 200, algasProd: 0.5, algasW: 1.0, algasEnPecera: false, algasNoche: 0.25, alga: 'espirulina', espirulinaG: 5, calentarAlgas: true,
    acuarioL: 500, peces: 10, alimentoPeces: 300, calentarPecera: true, tPecera: 28, salPecera: 2,
    panelW: 550, paneles: 20, bateriaKWh: 20.5, generadorKW: 7, combustible: 'gaslp', combustibleL: 600,
    cargaBase: 0.25, tSet: 17, calefKW: 3,
    aguaL: 20000, aguaPersona: 15, aguaPerro: 1.0, reciclaGris: 0.5, deshum: 0.8, deshumKWhL: 0.55, techo: 100, lluviaDia: 30,
    comidaDias: 900, croquetasKg: 1500,
    duchasSemana: 3.5, duchaMin: 3, regaderaLmin: 6, tDucha: 38, lombricomposta: true,
    salidaDia: 30, salidaH: 0.5, umbralSalida: 0.5,
  }, o);
}

function shieldPF(c) {
  // espesores de medio valor para rayos gamma de lluvia radiactiva: tierra 9.1 cm, concreto 6.1 cm
  const slab = Math.pow(2, c.tierra / 0.091 + c.concreto / 0.061);
  const entrada = [50, 300, 1000, 3000][clamp(c.vueltas, 0, 3)];
  return Math.min(slab, entrada);
}

function fuelLperKWh(f) { return { gaslp: 0.55, gasolina: 0.42, diesel: 0.28 }[f]; }
function fuelLife(f) { return { gaslp: Infinity, gasolina: 365, diesel: 730 }[f]; }

function simular(cin) {
  const c = config(cin);
  const sc = SCEN[c.escenario];
  const PF = shieldPF(c);
  const V = c.area * c.altura * 1000;                 // L de aire
  const molAir = P_ALT * 1000 * (V / 1000) / (R_GAS * T_REF); // mol totales
  // metabolismo: kcal → O2 y CO2 (mol/h)
  const kcalPerros = 105 * Math.pow(c.pesoPerro, 0.75) * c.perros;
  const kcalHum = c.kcalPersona * c.personas;
  const o2Met = (kcalHum + kcalPerros) / KCAL_PER_L_O2 * MOL_PER_L_STP / 24; // mol/h
  const co2Met = o2Met * RQ;
  const heatMet = (136.7 * c.personas + (kcalPerros * 4184 / 86400)) / 1000; // kW
  const vaporMet = (2.0 * c.personas + 0.4 * c.perros) / 24; // L/h

  const pvKWp = c.panelW * c.paneles / 1000;
  const fuelRate = fuelLperKWh(c.combustible);
  const s = {
    o2: 0.2095 * molAir, co2: 420e-6 * molAir, T: 18.3, Tg: 18.3, soc: 0.8 * c.bateriaKWh, fuel: c.combustibleL,
    agua: c.aguaL, comida: c.comidaDias * kcalHum, croq: c.croquetasKg, cal: c.calSodada, o2kg: c.o2kg,
    peces: c.peces, alimPeces: c.alimentoPeces, dosis: 0, dosisOut: 0, lastRecov: 0,
    co2aq: KH_CO2 * 420e-6 * P_ALT / 101.325 * c.acuarioL,   // mol de CO2 disuelto en la pecera
  };
  const s0 = { soc: s.soc, agua: s.agua, o2: s.o2, co2: s.co2, co2aq: s.co2aq };
  const days = [];
  const tot = { pv: 0, gen: 0, load: 0, shed: 0, shedVital: 0, ch: 0, dis: 0, lossDis: 0, aguaIn: 0, aguaOut: 0, aguaRebose: 0, aguaFalta: 0, o2Src: 0, o2Vent: 0, o2Bottle: 0, co2Src: 0, co2Vent: 0, co2Scrub: 0, co2Aq: 0, kcalProd: 0, kcalFalta: 0, croqFalta: 0, pescadoKg: 0, algasComidaKg: 0, algasPecesKg: 0, lombrizKg: 0 };
  const firsts = {};
  const mark = (k, d) => { if (firsts[k] === undefined) firsts[k] = d; };
  const ventQ = c.vent * 1000; // L/h
  const crop = (area, name, ppfd) => ({ area, cr: CROPS[name], ppfd });
  const cultivos = [crop(c.hidroArea, c.hidroCultivo, c.hidroPPFD), crop(c.aeroArea, c.aeroCultivo, c.aeroPPFD)];
  const ledKW = cultivos.reduce((a, k) => a + k.area * k.ppfd / c.ledEff / 1000, 0);
  const algKW = c.algasL * c.algasW / 1000;

  for (let d = 0; d < c.dias; d++) {
    const m = Math.floor((d % 365) / 30.42) % 12;
    // forzamiento del hollín (sube en semanas, decae con vida e de 4.6 años) y respuesta retrasada del clima
    const f = (1 - Math.exp(-d / SOOT_RISE_D)) * Math.exp(-d / SOOT_EFOLD_D);
    const fT = d === 0 ? 0 : days[d - 1].fT + (f - days[d - 1].fT) / TEMP_LAG_D;
    const Tout = T_NORMAL[m] - sc.dT * fT / 0.8;
    // con el cielo oscuro el día calienta menos y la oscilación diaria se achica
    const Tmin = Tout - DTR[m] / 2 * Math.sqrt(1 - sc.light * f);
    const luz = 1 - sc.light * f;
    const lluviaFac = 1 - sc.rain * fT / 0.8;
    const day = { d, f, fT, Tout, Tmin, luz, rainFac: lluviaFac, o2min: 1, co2max: 0, o2: 0, co2: 0, T: 0, pv: 0, gen: 0, shed: 0, kcalProd: 0,
      o2Plant: 0, o2Alg: 0, o2Fish: 0, o2Met: 0, o2Vent: 0, calUsed: 0, lluvia: 0, rateOut: 0, rateIn: 0, ledOnFrac: 0, aguaFalta: 0, shedVital: 0, co2Aq: 0, Taq: 0, vitC: 0, algasG: 0, algasComidaG: 0, duchaFrac: 0, residuosG: 0,
      w: { recambio: 0, lluvia: 0, condensado: 0, grises: 0, beber: 0, cocina: 0, higiene: 0, perros: 0, plantas: 0, pecera: 0, vaporPerdido: 0, negras: 0 } };
    const sealed = d < c.sellarDias;
    s.Tg += ((18.3 - sc.dT * fT / 0.8) - s.Tg) / 365;   // la tierra alrededor se enfría despacio
    let ledHours = 0;
    for (let h = 0; h < 24; h++) {
      const tH = d * 24 + h + 1; // horas desde la detonación
      // 1. Radiación: regla t^-1.2 desde la llegada de la lluvia radiactiva
      const rate = tH >= c.llegadaH ? c.tasaH1 * Math.pow(tH, -1.2) : 0;
      const outside = d >= c.salidaDia && rate < c.umbralSalida && h === 12 && c.salidaH > 0;
      const dIn = rate / PF, dOut = outside ? rate * c.salidaH * 0.7 : 0;  // afuera: terreno real ≈ 0.7 del ideal
      s.dosis += dIn + dOut; s.dosisOut += rate;
      day.rateOut = Math.max(day.rateOut, rate); day.rateIn = Math.max(day.rateIn, dIn);

      // 2. Energía: panel → cargas por prioridad → batería → generador; lo que falta se apaga de abajo hacia arriba
      const sun = h >= 6 && h < 18 ? Math.sin(Math.PI * (h - 6 + 0.5) / 12) * Math.PI / 24 : 0; // suma 1 en el día
      const pv = pvKWp * PV_YIELD[m] * luz * sun;
      const lights = h >= 6 && h < 6 + c.fotoperiodo;
      // ventilación: caudal normal y, si hace calor dentro y afuera está más fresco, caudal de enfriamiento
      const cool = !sealed && s.T > 25 && Tout < s.T - 2;
      const ventFlow = sealed ? 0 : cool ? Math.max(c.vent, c.ventMax) : c.vent;
      const ventKW = sealed ? 0.02 : ventFlow * c.ventW / 1000;
      // pecera: pierde ~20 W/K por cada 500 L (con tapa y aislamiento lateral); la tilapia muere abajo de ~11 °C
      const UAaq = c.acuarioL > 0 ? 0.020 * Math.pow(c.acuarioL / 500, 2 / 3) : 0;
      const aqKW = c.calentarPecera ? Math.max(0, UAaq * (c.tPecera - s.T)) : 0;
      const aire = c.acuarioL > 0 ? 0.03 * c.acuarioL / 500 : 0;          // aireador: sin él los peces se asfixian en horas
      const vital = [['vent', ventKW], ['base', c.cargaBase], ['calef', s.T < c.tSet ? c.calefKW : 0], ['pecera', aqKW + aire]];
      const al = ALGAS[c.alga];
      const UAalg = c.algasL > 0 && !c.algasEnPecera ? 0.020 * Math.pow(c.algasL / 500, 2 / 3) : 0;
      const algHeatKW = c.calentarAlgas && UAalg ? Math.max(0, UAalg * (al.tOpt - s.T)) : 0;
      // regadera: agua de la cisterna (a la temperatura del cuarto) calentada a 38 °C, repartida en el día
      const duchaL = c.duchasSemana / 7 * c.duchaMin * c.regaderaLmin * c.personas;
      const duchaKW = duchaL * 4.186 * Math.max(0, c.tDucha - s.T) / 3600 / 0.95 / 24;
      const extra = [['deshum', s.lastRecov * c.deshumKWhL], ['ducha', duchaKW], ['algas', (lights ? algKW : 0) + algHeatKW], ['led', lights ? ledKW : 0]];
      const served = {};
      let pvLeft = pv, gen = 0, short = 0, ch = 0;
      const discharge = (kwh, floor) => {          // entrega kwh desde la batería sin bajar de floor
        const dis = Math.min(kwh / 0.95, Math.max(0, s.soc - floor * c.bateriaKWh));
        s.soc -= dis; tot.dis += dis; tot.lossDis += dis * 0.05; return dis * 0.95;
      };
      // a) cargas vitales: panel → batería hasta 10 % → generador
      let needV = vital.reduce((a, l) => a + l[1], 0);
      const fromPV = Math.min(pvLeft, needV); pvLeft -= fromPV; needV -= fromPV;
      needV -= discharge(needV, 0.1);
      if ((needV > 1e-9 || s.soc < 0.25 * c.bateriaKWh) && s.fuel > 0 && d < fuelLife(c.combustible) && c.generadorKW > 0) {
        const cap = Math.min(c.generadorKW, s.fuel / fuelRate);
        const toLoad = Math.min(needV, cap);
        const toBat = s.soc < 0.25 * c.bateriaKWh ? Math.max(0, Math.min((cap - toLoad) * 0.95, 0.9 * c.bateriaKWh - s.soc)) : 0;
        gen = toLoad + toBat / 0.95;
        s.soc += toBat; tot.ch += toBat / 0.95;
        needV -= toLoad; s.fuel -= gen * fuelRate;
      }
      let cut = Math.max(0, needV); short += cut; tot.shedVital += cut; day.shedVital += cut;
      for (let i = vital.length - 1; i >= 0; i--) { const [k, w] = vital[i]; const x = Math.min(cut, w); served[k] = w - x; cut -= x; }
      // b) asegura la noche: el panel carga la batería hasta 60 % antes de alimentar cultivos
      const pre = Math.max(0, Math.min(pvLeft * 0.95, 0.6 * c.bateriaKWh - s.soc));
      s.soc += pre; tot.ch += pre / 0.95; pvLeft -= pre / 0.95; ch += pre;
      // c) cargas de cultivo y agua: sólo excedente del panel o batería arriba de 50 %
      for (const [k, w] of extra) {
        let give = Math.min(pvLeft, w); pvLeft -= give;
        give += discharge(w - give, 0.5);
        served[k] = give; short += w - give;
      }
      // d) lo que sobra del panel carga la batería; el resto se tira
      const post = Math.max(0, Math.min(pvLeft * 0.95, 0.95 * c.bateriaKWh - s.soc));
      s.soc += post; tot.ch += post / 0.95; pvLeft -= post / 0.95; ch += post;
      const pvUsed = pv - pvLeft;
      const loads = [...vital, ...extra];
      tot.pv += pvUsed; tot.gen += gen; tot.shed += short;
      for (const k in served) tot.load += served[k];
      day.pv += pvUsed; day.gen += gen; day.shed += short;
      const ledFrac = lights && ledKW > 0 ? served.led / ledKW : 0;
      const algDemand = (lights ? algKW : 0) + algHeatKW;
      const algServed = algDemand > 0 ? served.algas / algDemand : 1;
      const algFrac = lights && algKW > 0 ? algServed : 0;
      // temperatura del cultivo: en la pecera es la del agua; aparte, la del cuarto más lo que alcance el calentador
      const Talg = c.algasEnPecera ? null : (c.calentarAlgas ? s.T + algServed * (al.tOpt - s.T) : s.T);
      const ventOn = sealed ? 0 : (ventKW > 0 ? served.vent / ventKW : 1) * ventFlow / Math.max(1e-9, c.vent);
      const deshFrac = extra[0][1] > 0 ? served.deshum / extra[0][1] : 1;
      day.duchaFrac += (duchaKW > 0 ? served.ducha / duchaKW : 1) / 24;
      const aqFrac = aqKW + aire > 0 ? Math.min(1, served.pecera / (aqKW + aire)) : (c.calentarPecera ? 1 : 0);
      const Taq = c.calentarPecera ? s.T + aqFrac * (c.tPecera - s.T) : s.T;
      day.Taq += Taq / 24;
      if (lights) ledHours += ledFrac;

      // 3. Fotosíntesis de plantas y algas (sólo con luz)
      let o2P = 0, co2P = 0, transp = 0, kcalH = 0;
      for (const k of cultivos) {
        if (k.area <= 0 || !lights) continue;
        const mol = k.ppfd * 3600e-6 * k.area * ledFrac;  // mol de fotones en la hora
        const bio = mol * k.cr.lueTot;                     // g de biomasa seca
        o2P += bio * O2_PER_G_BIOMASS / 32; co2P += bio * CO2_PER_G_BIOMASS / 44; transp += bio * TRANSP_L_PER_G;
        if (d >= k.cr.cycle) { kcalH += mol * k.cr.lueEd * k.cr.kcal; day.vitC += mol * k.cr.lueEd * k.cr.vitC; }
        day.residuosG += mol * (k.cr.lueTot - k.cr.lueEd);            // hojas, tallos y raíces
      }
      // en la pecera el agua es turbia y está sombreada: ~30 % de la productividad de un fotobiorreactor
      // la espirulina necesita agua alcalina y salada que mataría a la tilapia: no puede ir en la pecera
      const tAlg = c.algasEnPecera ? Taq : Talg;
      const gAlg = clamp((tAlg - al.tMin) / (al.tOpt - al.tMin), 0, 1);
      const compatible = !(c.algasEnPecera && !al.enPecera);
      const algProd = compatible ? c.algasProd * (c.algasEnPecera ? 0.3 : 1) * gAlg : 0;
      const algDay = c.algasL * algProd / c.fotoperiodo;
      const algBio = lights && c.algasL > 0 ? algDay * algFrac : 0;
      // de noche las algas respiran una parte de lo que produjeron de día
      const algResp = !lights && c.algasL > 0 ? algDay * c.fotoperiodo * c.algasNoche / (24 - c.fotoperiodo) : 0;
      const o2A = (algBio - algResp) * 1.4 / 32, co2A = (algBio - algResp) * 1.9 / 44;   // con nitrato como fuente de N (calibrado)
      day.algasG += algBio;
      // 4. Peces: respiran todo el día (150 mg O2/kg/h)
      const fishO2 = s.peces * 150e-3 / 32;

      // 5. Aire: balance de moles con ventilación filtrada (implícito)
      const o2Src = -o2Met - fishO2 + o2P + o2A;
      const co2Src = co2Met + fishO2 * 0.9 - co2P - co2A;
      const Qn = ventOn * ventQ / V;               // recambios por hora (ventOn incluye el caudal de enfriamiento)
      const o2Out = 0.2095 * molAir, co2Out = 420e-6 * molAir;
      const o2Prev = s.o2, co2Prev = s.co2;
      s.o2 = (s.o2 + o2Src + Qn * o2Out) / (1 + Qn);
      s.co2 = (s.co2 + co2Src + Qn * co2Out) / (1 + Qn);
      tot.o2Src += o2Src; tot.o2Vent += s.o2 - o2Prev - o2Src;
      tot.co2Src += co2Src; tot.co2Vent += s.co2 - co2Prev - co2Src;
      // la pecera disuelve CO2 hasta el equilibrio de Henry y luego ya no absorbe más
      if (c.acuarioL > 0) {
        const eq = KH_CO2 * (s.co2 / molAir) * P_ALT / 101.325 * c.acuarioL;
        const flux = (eq - s.co2aq) * (1 - Math.exp(-1));   // kLa·dt = 1
        s.co2aq += flux; s.co2 -= flux; tot.co2Aq += flux; day.co2Aq += flux;
      }
      // depurador de cal sodada (0.5 kg CO2/kg) cuando el CO2 pasa de 5 000 ppm
      let calUse = 0;
      if (s.co2 / molAir > 0.005 && s.cal > 0) {
        calUse = Math.min(s.cal, (s.co2 - 0.004 * molAir) * 0.044 / 0.5);
        s.co2 -= calUse * 0.5 / 0.044; s.cal -= calUse; tot.co2Scrub += calUse * 0.5 / 0.044;
      }
      // oxígeno embotellado si baja de 19 %
      if (s.o2 / molAir < 0.19 && s.o2kg > 0) {
        const add = Math.min(s.o2kg, (0.195 * molAir - s.o2) * 0.032);
        s.o2 += add / 0.032; s.o2kg -= add; tot.o2Bottle += add / 0.032;
      }
      day.o2Met += o2Met; day.o2Plant += o2P; day.o2Alg += o2A; day.o2Fish += fishO2; day.calUsed += calUse;
      day.o2Vent += s.o2 - o2Prev - o2Src;
      const o2f = s.o2 / molAir, co2f = s.co2 / molAir;
      day.o2min = Math.min(day.o2min, o2f); day.co2max = Math.max(day.co2max, co2f);
      day.o2 += o2f / 24; day.co2 += co2f / 24;

      // 6. Temperatura: tierra, aire de ventilación (con recuperador), gente, perros, focos y calefacción
      let gains = heatMet;
      for (const k in served) gains += served[k];
      const UAg = 0.75 * (2 * c.area + 4 * Math.sqrt(c.area) * c.altura) / 1000;      // kW/K hacia la tierra
      const UAv = ventOn * c.vent * 1.0 * 1.005 / 3600 * (cool ? 1 : 1 - c.recupCalor); // kW/K del aire que entra; sin recuperador si enfría
      s.T = (s.T * CTH + gains + UAg * s.Tg + UAv * Tout) / (CTH + UAg + UAv);
      day.T += s.T / 24;

      // 7. Agua: consumo, vapor recuperado por el deshumidificador, aguas grises y lluvia
      const use = (c.aguaPersona * c.personas + c.aguaPerro * c.perros) / 24;
      const evapAcu = c.acuarioL * 0.01 / 24;
      const vapor = vaporMet + transp + evapAcu;
      const recov = vapor * c.deshum * deshFrac;
      s.lastRecov = vapor * c.deshum;
      // de cada persona: 3 L para beber, 3 L para cocinar, el resto para higiene; las grises son higiene y la mitad de la cocina
      const beber = Math.min(3, c.aguaPersona) * c.personas / 24, cocina = Math.min(3, Math.max(0, c.aguaPersona - 3)) * c.personas / 24;
      const higiene = Math.max(0, c.aguaPersona - 6) * c.personas / 24;
      const grey = (higiene + 0.5 * cocina) * c.reciclaGris;
      const rain = d >= c.lluviaDia ? c.techo * RAIN_MM[m] / 30.42 / 24 * 0.8 * lluviaFac : 0;
      // el recambio de la pecera (1.5 % al día) sale de la cisterna y riega las plantas: abono para ellas
      const recambio = c.acuarioL * 0.015 / 24;
      const riegoTanque = Math.max(0, transp - recambio);
      const inflow = recov + grey + rain, outflow = use + recambio + riegoTanque + evapAcu;
      const want = s.agua + inflow - outflow;
      const next = clamp(want, 0, c.aguaL);
      tot.aguaIn += inflow; tot.aguaOut += outflow; tot.aguaRebose += Math.max(0, want - next); tot.aguaFalta += Math.max(0, next - want);
      day.aguaFalta += Math.max(0, next - want);
      s.agua = next; day.lluvia += rain;
      const w = day.w;
      w.lluvia += rain; w.condensado += recov; w.grises += grey; w.beber += beber; w.cocina += cocina; w.higiene += higiene;
      w.perros += c.aguaPerro * c.perros / 24; w.plantas += riegoTanque; w.pecera += evapAcu + recambio; w.recambio += recambio; w.vaporPerdido += vapor - recov;
      w.negras += Math.max(0, beber + 0.5 * cocina - vaporMet * c.personas * 2.0 / (2.0 * c.personas + 0.4 * c.perros || 1));
      day.kcalProd += kcalH;
    }
    if (day.aguaFalta > 0) mark('agua', d);
    // comida del día
    // algas cosechadas: hasta el tope por persona se come (espirulina); lo que sobra es alimento para la tilapia
    if (d >= 14 && day.algasG > 0) {
      const al = ALGAS[c.alga];
      const comer = c.alga === 'espirulina' ? Math.min(day.algasG, c.espirulinaG * c.personas) : 0;
      day.algasComidaG = comer; day.kcalProd += comer * al.kcal;
      s.alimPeces += (day.algasG - comer) / 1000;                    // kg de alga seca como alimento de peces
      tot.algasComidaKg += comer / 1000; tot.algasPecesKg += (day.algasG - comer) / 1000;
    }
    // desechos: heces 128 g y orina 1.42 L por persona (Rose 2015); perros, en proporción a sus croquetas
    const croqDia = kcalPerros / 3500;
    const des = {
      hecesKg: 0.128 * c.personas, orinaL: 1.42 * c.personas,
      hecesPerrosKg: 0.82 * croqDia, orinaPerrosL: 0.04 * c.pesoPerro * c.perros,
      aserrinKg: 0.030 * 1.2 * c.personas + 0.2 * c.perros,           // 30 g por uso; arena de aserrín para los perros
      restosKg: day.residuosG / 1000 * 5,                              // restos de cultivo frescos (≈ 20 % materia seca)
      basuraKg: 0.05 * c.personas,                                     // empaques de la comida guardada
    };
    // lombricomposta: las lombrices se comen los restos de cultivo; ~10 % se vuelve lombriz, alimento para la tilapia
    if (c.lombricomposta && des.restosKg > 0) { const lomb = 0.10 * des.restosKg * 0.2; s.alimPeces += lomb; tot.lombrizKg += lomb; }
    for (const k in des) tot[k] = (tot[k] || 0) + des[k];
    day.des = des;
    const gT = clamp((day.Taq - 18) / 10, 0, 1);                       // crecen bien a 28 °C, casi nada a 18 °C
    if (s.peces > 0 && day.Taq < 11) { mark('peces mueren de frío', d); day.kcalProd += s.peces * 960; s.peces = 0; }
    const feedNeed = s.peces * 0.015 * gT;                             // 1.5 % del peso al día si el agua está tibia
    const fishFeed = Math.min(s.alimPeces, feedNeed);
    s.alimPeces -= fishFeed; s.peces += fishFeed / 1.8;                // conversión alimenticia 1.8
    if (s.peces > 0 && feedNeed > 0 && fishFeed < feedNeed * 0.999) {  // sin alimento: se cosechan todos
      mark('alimento de peces', d); day.kcalProd += s.peces * 960; s.peces = 0;
    }
    const maxFish = c.acuarioL / 1000 * 25;
    if (s.peces > maxFish) { day.kcalProd += (s.peces - maxFish) * 960; tot.pescadoKg += s.peces - maxFish; s.peces = maxFish; }
    const need = kcalHum - day.kcalProd;
    tot.kcalProd += Math.min(day.kcalProd, kcalHum);
    if (need > 0) { const take = Math.min(s.comida, need); s.comida -= take; if (take < need) { tot.kcalFalta += need - take; mark('comida', d); } }
    const croqNeed = kcalPerros / 3500;
    const croqTake = Math.min(s.croq, croqNeed); s.croq -= croqTake;
    if (croqTake < croqNeed) { tot.croqFalta += croqNeed - croqTake; mark('croquetas', d); }
    if (c.combustibleL > 0 && s.fuel <= 1e-6) mark('combustible', d);
    if (c.combustibleL > 0 && d >= fuelLife(c.combustible)) mark('combustible caducado', d);
    if (c.calSodada > 0 && s.cal <= 1e-6) mark('cal sodada', d);
    if (day.co2max > 0.005) mark('CO₂ arriba de 5 000 ppm', d);
    if (day.co2max > 0.03) mark('CO₂ peligroso (3 %)', d);
    if (day.o2min < 0.195) mark('oxígeno bajo (19.5 %)', d);
    if (day.T < 12) mark('frío dentro (< 12 °C)', d);
    if (day.T > 30) mark('calor dentro (> 30 °C)', d);
    if (day.shedVital > 0.05) mark('se apagan cargas vitales', d);
    if (day.ledOnFrac < 0.5) mark('cultivos con menos de la mitad de luz', d);
    Object.assign(day, {
      agua: s.agua, comida: s.comida / kcalHum, croq: s.croq / croqNeed, fuel: s.fuel, soc: c.bateriaKWh ? s.soc / c.bateriaKWh : 0,
      cal: s.cal, dosis: s.dosis, peces: s.peces, alimPeces: s.alimPeces, co2aqMol: s.co2aq, ledOnFrac: c.fotoperiodo ? ledHours / c.fotoperiodo : 0, o2kg: s.o2kg,
    });
    days.push(day);
  }
  return { c, days, tot, firsts, s0, end: s, PF, molAir, V, ledKW, algKW, pvKWp, kcalHum, kcalPerros, o2Met, co2Met, scen: sc };
}

// Necesidades de diseño para 3 años: lo que habría que guardar o producir
function necesidades(c) {
  const r = simular(Object.assign({}, c, { dias: 1 }));
  const kcalPerros = r.kcalPerros;
  return {
    comidaKg: c.kcalPersona * c.personas * c.dias / 3500, croquetasKg: kcalPerros * c.dias / 3500,
    aguaSinReciclar: (c.aguaPersona * c.personas + c.aguaPerro * c.perros) * c.dias,
    o2kgDia: r.o2Met * 24 * 0.032, co2kgDia: r.co2Met * 24 * 0.044,
    calSodadaSellado: r.co2Met * 24 * 0.044 / 0.5,
    ventPara1000ppm: r.co2Met * R_GAS * T_REF / (P_ALT * 1000) / 0.00058,   // m3/h
    areaO2: r.o2Met * 24 * 32 / O2_PER_G_BIOMASS / (c.aeroPPFD * 3600e-6 * c.fotoperiodo * CROPS.papa.lueTot),
    areaComida: c.kcalPersona * c.personas / (c.aeroPPFD * 3600e-6 * c.fotoperiodo * CROPS.papa.lueEd * CROPS.papa.kcal),
    salPersonasKg: 0.005 * c.personas * c.dias,                                  // 5 g por persona al día
    salPeceraKg: c.acuarioL * c.salPecera / 1000 * (1 + 0.015 * c.dias),         // carga inicial + recambio de 1.5 % al día
    // espirulina: carga inicial de 16.8 g/L de bicarbonato y reposición; nitrato ≈ 0.7 g por g de alga
    bicarbonatoKg: c.alga === 'espirulina' && !c.algasEnPecera ? c.algasL * 0.0168 + c.algasL * c.algasProd * c.dias * 1.0 / 1000 : 0,
    nitratoKg: c.algasL * c.algasProd * c.dias * 0.7 / 1000,
    banos: Math.max(1, Math.ceil(c.personas / 5)),
    duchaL: c.duchasSemana / 7 * c.duchaMin * c.regaderaLmin,                    // L por persona al día
    // composta de heces + aserrín (≈ 0.5 kg/L), cámaras para 12 meses cada una (se alternan)
    camaraL: (0.128 * c.personas + 0.036 * c.personas) * 365 / 0.5,
    orinaL: 1.42 * c.personas * c.dias,
    aserrinKg: (0.036 * c.personas + 0.2 * c.perros) * c.dias,
  };
}
// MODEL-END
if (typeof module !== 'undefined') module.exports = { simular, config, necesidades, shieldPF, SCEN, CROPS, ALGAS, T_NORMAL, RAIN_MM, DTR };
