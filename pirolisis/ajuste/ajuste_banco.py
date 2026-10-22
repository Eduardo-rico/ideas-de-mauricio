"""Ajusta selectividades y craqueo secundario a corridas de un reactor de banco.

La cinética primaria (A, Ea) viene de la TGA (cinetica_tga.py). Aquí se ajusta
lo que la TGA no puede ver: en qué productos se rompe el plástico y qué tan rápido
se siguen rompiendo ceras, diésel y gasolina dentro del reactor.

Uso:
    uv run python ajuste_banco.py banco.csv --tga resultados/cinetica_tga.json --salida resultados/
    uv run python ajuste_banco.py banco.csv --tga ... --validar banco_validacion.csv

Columnas del CSV (una fila por corrida):
    corrida, masa_kg, volumen_m3, T_C, P_bar, reflujo (si/no), T_defleg_C, T_cond_C, n2_mol_s,
    catalizador (none/FCC/HY/ZSM5), carga_cat, gasolina_kg, diesel_kg, ceras_kg, gas_kg, coque_kg
Opcionales: potencia_kW, UA_W_K, masa_acero_kg. Si gas_kg viene vacío se calcula por diferencia.
"""
import argparse
import copy
import csv
import json
import math
import pathlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy.optimize import least_squares

import modelo

PRODUCTOS = [("gasolina_kg", "G"), ("diesel_kg", "D"), ("ceras_kg", "W"), ("gas_kg", "gas"), ("coque_kg", "char")]
S_KEYS = ["W", "D", "G", "Gs", "C"]
SEC_KEYS = ["W", "D", "G"]
T_REF_SEC = 723.15  # K; las constantes secundarias se reportan a 450 °C


def config_de_fila(f, mix):
    masa = float(f["masa_kg"])
    extra = {}
    if f.get("UA_W_K"):
        extra["UA"] = float(f["UA_W_K"])
    if f.get("masa_acero_kg"):
        extra["mSteel"] = float(f["masa_acero_kg"])
    return modelo.config(
        mix=mix, mass=masa, Vr=float(f["volumen_m3"]), Tsp=float(f["T_C"]) + 273.15, Pset=float(f["P_bar"]) * 1e5,
        reflux=str(f["reflujo"]).strip().lower() in ("si", "sí", "1", "true"), Tref=float(f["T_defleg_C"]) + 273.15,
        Tc=float(f["T_cond_C"]) + 273.15, n2=float(f["n2_mol_s"]), cat=(f.get("catalizador") or "none").strip(),
        catLoad=float(f.get("carga_cat") or 0), recirc=False,
        Pmax=float(f.get("potencia_kW") or max(2.0, 0.8 * masa)) * 1000, **extra,
    )


def leer_corridas(ruta):
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        filas = list(csv.DictReader(f))
    for f in filas:
        medidos = {k: (float(f[col]) if str(f.get(col, "")).strip() else None) for col, k in PRODUCTOS}
        if medidos["gas"] is None:
            medidos["gas"] = float(f["masa_kg"]) - sum(v for k, v in medidos.items() if k != "gas" and v is not None)
        faltan = [k for k, v in medidos.items() if v is None]
        if faltan:
            raise ValueError(f"Corrida {f.get('corrida')}: faltan productos {faltan}")
        f["_medido"] = medidos
        cierre = sum(medidos.values()) / float(f["masa_kg"])
        if abs(cierre - 1) > 0.05:
            print(f"⚠ Corrida {f.get('corrida')}: los productos suman {cierre * 100:.1f} % de la carga. "
                  "Un balance de masa que no cierra a ±5 % mete error al ajuste.")
    return filas


def primaria_desde_tga(ruta):
    d = json.loads(pathlib.Path(ruta).read_text())
    return d["simulador"]["POLY"], d["simulador"]["mix"]


# ---- parámetros ajustables ↔ vector x ----
def _softmax(z):
    z = np.concatenate([z, [0.0]])
    e = np.exp(z - z.max())
    return e / e.sum()


def aplicar(x, base, ajustar_ea):
    """Copia de parámetros con selectividades y craqueo secundario de x."""
    p = copy.deepcopy(base)
    s = _softmax(np.asarray(x[:4]))
    for poly in p["POLY"].values():
        poly["s"] = dict(zip(S_KEYS, map(float, s)))
    for n, i in enumerate(SEC_KEYS):
        q = p["SEC"][i]
        Ea = x[7 + n] * 1000 if ajustar_ea else q["Ea"]
        k_ref = 10.0 ** x[4 + n]
        q["Ea"] = Ea
        q["A"] = k_ref * math.exp(Ea / (modelo.R * T_REF_SEC))
    return p


def x_inicial(base, ajustar_ea):
    s = next(iter(base["POLY"].values()))["s"]
    v = np.log(np.array([max(1e-4, s[k]) for k in S_KEYS]))
    z = v[:4] - v[4]
    lk = [math.log10(base["SEC"][i]["A"] * math.exp(-base["SEC"][i]["Ea"] / (modelo.R * T_REF_SEC))) for i in SEC_KEYS]
    x = list(z) + lk
    if ajustar_ea:
        x += [base["SEC"][i]["Ea"] / 1000 for i in SEC_KEYS]
    return np.array(x)


def _simular_una(args):
    fila, mix, p, dt = args
    r = modelo.simular(config_de_fila(fila, mix), p, dt=dt)
    return [r[k] for _, k in PRODUCTOS]


class Ajustador:
    def __init__(self, corridas, poly, mix, ajustar_ea=False, dt=1.0, procesos=None):
        self.corridas, self.mix, self.ajustar_ea, self.dt = corridas, mix, ajustar_ea, dt
        self.base = modelo.parametros(POLY=poly)
        self.medido = np.array([[f["_medido"][k] for _, k in PRODUCTOS] for f in corridas])
        self.masa = np.array([float(f["masa_kg"]) for f in corridas])
        self.pool = ProcessPoolExecutor(procesos) if procesos != 1 else None

    def predecir(self, x, corridas=None):
        corridas = corridas or self.corridas
        p = aplicar(x, self.base, self.ajustar_ea)
        trabajos = [(f, self.mix, p, self.dt) for f in corridas]
        res = list(self.pool.map(_simular_una, trabajos)) if self.pool else [_simular_una(t) for t in trabajos]
        return np.array(res)

    def residuos(self, x):
        return ((self.predecir(x) - self.medido) / self.masa[:, None]).ravel()

    def ajustar(self):
        x0 = x_inicial(self.base, self.ajustar_ea)
        n = len(x0)
        lo = [-8] * 4 + [-8] * 3 + ([80] * 3 if self.ajustar_ea else [])
        hi = [8] * 4 + [2] * 3 + ([320] * 3 if self.ajustar_ea else [])
        if len(self.corridas) * len(PRODUCTOS) <= n:
            raise ValueError(f"Con {len(self.corridas)} corridas no alcanza para {n} parámetros. Haz al menos 4.")
        sol = least_squares(self.residuos, x0, bounds=(lo, hi), diff_step=1e-2, x_scale="jac", max_nfev=60 * n)
        dof = max(1, sol.fun.size - n)
        s2 = float(np.sum(sol.fun ** 2) / dof)
        try:
            cov = np.linalg.inv(sol.jac.T @ sol.jac) * s2
            err = np.sqrt(np.clip(np.diag(cov), 0, None))
            d = np.sqrt(np.clip(np.diag(cov), 1e-300, None))
            corr = cov / np.outer(d, d)
        except np.linalg.LinAlgError:
            err, corr = np.full(n, np.nan), np.full((n, n), np.nan)
        return sol, err, corr, math.sqrt(s2)

    def cerrar(self):
        if self.pool:
            self.pool.shutdown()


def reporte(aj, sol, err, corr, rmse):
    p = aplicar(sol.x, aj.base, aj.ajustar_ea)
    s = next(iter(p["POLY"].values()))["s"]
    nombres = ["z_W", "z_D", "z_G", "z_Gs"] + [f"log10 k_{i}(450 °C)" for i in SEC_KEYS] + \
              ([f"Ea_{i}" for i in SEC_KEYS] if aj.ajustar_ea else [])
    print(f"\nError típico del ajuste: {rmse * 100:.2f} % de la carga por producto")
    print("\nSelectividad primaria (fracción de masa):")
    for k, n in zip(S_KEYS, ["ceras", "diésel", "gasolina", "gas", "coque"]):
        print(f"  {n:9s} {s[k]:.3f}")
    print("\nCraqueo secundario:")
    for n, i in enumerate(SEC_KEYS):
        q = p["SEC"][i]
        k = q["A"] * math.exp(-q["Ea"] / (modelo.R * T_REF_SEC))
        rel = err[4 + n] * math.log(10)
        txt = f"  {i}: k(450 °C) = {k:.3e} 1/s (± {rel * 100:.0f} %) · Ea {q['Ea'] / 1000:.0f} kJ/mol"
        if aj.ajustar_ea:
            txt += f" ± {err[7 + n]:.0f}"
        print(txt + f" · A {q['A']:.3e} 1/s")
    altas = [(nombres[i], nombres[j], corr[i, j]) for i in range(len(nombres)) for j in range(i + 1, len(nombres))
             if abs(corr[i, j]) > 0.95]
    for a, b, r in altas:
        print(f"⚠ {a} y {b} están correlacionados ({r:+.2f}): las corridas no los separan. "
              "Agrega corridas que cambien temperatura, presión o reflujo.")
    if any(e * math.log(10) > 1.0 for e in err[4:7]):
        print("⚠ Alguna constante secundaria tiene incertidumbre mayor que ×2.7: tómala como orden de magnitud.")
    return p


def tabla(corridas, pred, medido):
    print("\nCorrida    " + "  ".join(f"{n:>17s}" for n in ["gasolina", "diésel", "ceras", "gas", "coque"]))
    for f, pr, me in zip(corridas, pred, medido):
        m = float(f["masa_kg"])
        print(f"{f['corrida']:10s} " + "  ".join(f"{100 * a / m:6.1f}% vs {100 * b / m:5.1f}%" for a, b in zip(pr, me)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--tga", required=True, help="cinetica_tga.json de cinetica_tga.py")
    ap.add_argument("--ajustar-ea", action="store_true", help="ajustar también Ea secundarias (requiere ≥ 3 temperaturas)")
    ap.add_argument("--validar", help="CSV con corridas que NO se usan para ajustar, sólo para comprobar")
    ap.add_argument("--salida", default="resultados")
    a = ap.parse_args(argv)

    corridas = leer_corridas(a.csv)
    poly, mix = primaria_desde_tga(a.tga)
    temps = {float(f["T_C"]) for f in corridas}
    if a.ajustar_ea and len(temps) < 3:
        raise SystemExit("Para --ajustar-ea hacen falta corridas a 3 temperaturas distintas por lo menos.")
    aj = Ajustador(corridas, poly, mix, a.ajustar_ea)
    try:
        print(f"Ajustando {len(corridas)} corridas ({len(x_inicial(aj.base, a.ajustar_ea))} parámetros)…")
        sol, err, corr, rmse = aj.ajustar()
        p = reporte(aj, sol, err, corr, rmse)
        pred = aj.predecir(sol.x)
        print("\nAjustadas (modelo vs medido, % de la carga):")
        tabla(corridas, pred, aj.medido)
        val = None
        if a.validar:
            cv = leer_corridas(a.validar)
            pv = aj.predecir(sol.x, cv)
            mv = np.array([[f["_medido"][k] for _, k in PRODUCTOS] for f in cv])
            ev = float(np.sqrt(np.mean(((pv - mv) / np.array([float(f["masa_kg"]) for f in cv])[:, None]) ** 2)))
            print(f"\nValidación con corridas no usadas en el ajuste (error típico {ev * 100:.2f} %):")
            tabla(cv, pv, mv)
            val = ev
    finally:
        aj.cerrar()

    carpeta = pathlib.Path(a.salida)
    carpeta.mkdir(parents=True, exist_ok=True)
    out = {"rmse_fraccion": rmse, "rmse_validacion": val, "s": next(iter(p["POLY"].values()))["s"],
           "SEC": p["SEC"], "POLY": p["POLY"], "mix": mix}
    (carpeta / "ajuste_banco.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\nGuardado: {carpeta / 'ajuste_banco.json'}")


if __name__ == "__main__":
    main()
