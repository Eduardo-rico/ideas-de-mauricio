"""Cinética de pirólisis a partir de termogravimetría (TGA) a varias velocidades de calentamiento.

Tres métodos, del más robusto al más completo:
  1. Friedman (isoconversional diferencial): Ea en cada grado de conversión α, sin suponer modelo.
  2. KAS, Kissinger–Akahira–Sunose (isoconversional integral): comprobación independiente de Ea(α).
  3. Ajuste global de N reacciones paralelas de orden n, una por plástico de la mezcla.
     Sus A y Ea son las que usa el simulador.

Uso:
    uv run python cinetica_tga.py datos_tga.csv --componentes 3 --salida resultados/

Formato del CSV (una fila por punto; todas las velocidades en el mismo archivo):
    velocidad_K_min, temperatura_C, masa        (masa en mg o en %; tiempo_s es opcional)
"""
import argparse
import csv
import json
import math
import pathlib
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares
from scipy.signal import find_peaks, savgol_filter

R = 8.314
T_REF = 700.0          # K; temperatura de referencia para desacoplar A y Ea en el ajuste
T_SECO = 150 + 273.15  # K; por debajo sólo se pierde humedad, no hay pirólisis


@dataclass
class Curva:
    beta: float        # K/s
    T: np.ndarray      # K, malla uniforme de 1 K
    alpha: np.ndarray  # conversión 0–1
    dadt: np.ndarray   # 1/s
    residuo: float     # fracción de masa que no se volatiliza (coque + inorgánicos)


def leer_csv(ruta):
    """Lee el CSV y regresa {beta_K_s: (T_K, masa)} ordenado por temperatura."""
    filas = {}
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            b = float(r["velocidad_K_min"]) / 60.0
            filas.setdefault(b, []).append((float(r["temperatura_C"]) + 273.15, float(r["masa"])))
    out = {}
    for b, pts in sorted(filas.items()):
        pts.sort()
        T, m = np.array(pts).T
        out[b] = (T, m)
    if len(out) < 3:
        raise ValueError(f"Se necesitan al menos 3 velocidades de calentamiento; el archivo tiene {len(out)}.")
    return out


def preparar(beta, T, m):
    """Conversión α(T) y velocidad dα/dt en una malla de 1 K, con la derivada suavizada."""
    sel = T >= T_SECO
    if sel.sum() < 50:
        raise ValueError(f"La curva a {beta * 60:.0f} K/min tiene muy pocos puntos arriba de 150 °C.")
    T, m = T[sel], m[sel]
    grid = np.arange(math.ceil(T[0]), math.floor(T[-1]) + 1, 1.0)
    mg = np.interp(grid, T, m)
    m0 = mg[0]
    minf = np.mean(mg[-max(5, len(mg) // 50):])
    alpha = np.clip((m0 - mg) / (m0 - minf), 0.0, 1.0)
    alpha = np.maximum.accumulate(alpha)
    win = min(31, (len(grid) // 2) * 2 - 1)
    dadT = np.clip(savgol_filter(alpha, win, 3, deriv=1, delta=1.0), 0.0, None)
    return Curva(beta=beta, T=grid, alpha=alpha, dadt=dadT * beta, residuo=float(minf / m0))


def _recta(x, y):
    A = np.vstack([x, np.ones_like(x)]).T
    (m, b), *_ = np.linalg.lstsq(A, y, rcond=None)
    yhat = m * x + b
    ss = np.sum((y - y.mean()) ** 2)
    r2 = 1 - np.sum((y - yhat) ** 2) / ss if ss > 0 else 1.0
    return m, b, r2


def _T_en(c, a):
    i = np.searchsorted(c.alpha, a)
    i = min(max(i, 1), len(c.alpha) - 1)
    a0, a1 = c.alpha[i - 1], c.alpha[i]
    t = 0.0 if a1 == a0 else (a - a0) / (a1 - a0)
    return c.T[i - 1] + t * (c.T[i] - c.T[i - 1])


def friedman(curvas, alphas=None):
    """ln(dα/dt) = ln[A f(α)] − Ea/(R T) a α fija. Regresa lista de dicts por α."""
    alphas = np.arange(0.1, 0.91, 0.05) if alphas is None else alphas
    res = []
    for a in alphas:
        Ts = np.array([_T_en(c, a) for c in curvas])
        r = np.array([np.interp(t, c.T, c.dadt) for t, c in zip(Ts, curvas)])
        if np.any(r <= 0):
            continue
        m, b, r2 = _recta(1 / Ts, np.log(r))
        res.append({"alpha": float(a), "Ea_kJ_mol": -m * R / 1000, "lnA_orden1": b - math.log(1 - a), "R2": r2})
    return res


def kas(curvas, alphas=None):
    """ln(β/T²) = cte − Ea/(R T) a α fija."""
    alphas = np.arange(0.1, 0.91, 0.05) if alphas is None else alphas
    res = []
    for a in alphas:
        Ts = np.array([_T_en(c, a) for c in curvas])
        betas = np.array([c.beta for c in curvas])
        m, _, r2 = _recta(1 / Ts, np.log(betas / Ts ** 2))
        res.append({"alpha": float(a), "Ea_kJ_mol": -m * R / 1000, "R2": r2})
    return res


def _desempacar(x, n, orden_libre):
    lk = x[0:n]                       # log10 k(T_REF), 1/s
    Ea = x[n:2 * n] * 1000            # J/mol
    if n > 1:
        z = np.concatenate([x[2 * n:3 * n - 1], [0.0]])
        frac = np.exp(z - z.max()); frac /= frac.sum()
        rest = x[3 * n - 1:]
    else:
        frac, rest = np.array([1.0]), x[2:]
    orden = rest[:n] if orden_libre else np.ones(n)
    return lk, Ea, frac, orden


def simular_alpha(T, beta, lk, Ea, frac, orden):
    """α(T) de N reacciones paralelas independientes bajo rampa lineal β."""
    kref = 10.0 ** np.asarray(lk)

    def f(t, a):
        k = kref * np.exp(-np.asarray(Ea) / R * (1 / t - 1 / T_REF))
        return k / beta * np.clip(1 - a, 0, 1) ** np.asarray(orden)

    sol = solve_ivp(f, (T[0], T[-1]), np.zeros(len(lk)), t_eval=T, method="LSODA", rtol=1e-7, atol=1e-10)
    if not sol.success or sol.y.shape[1] != len(T):
        return np.full(len(T), np.nan)
    return np.clip(sol.y, 0, 1).T @ np.asarray(frac)


def _semilla(curvas, n, fr):
    """Ea inicial de Friedman; k_ref de cada componente a partir de los picos de dα/dT."""
    c = curvas[len(curvas) // 2]
    Ea0 = float(np.median([r["Ea_kJ_mol"] for r in fr])) if fr else 200.0
    dadT = c.dadt / c.beta
    picos, prop = find_peaks(dadT, prominence=dadT.max() * 0.03, distance=8)
    if len(picos) >= n:
        picos = np.sort(picos[np.argsort(prop["prominences"])[-n:]])
        Tp = c.T[picos]
    else:
        lo, hi = _T_en(c, 0.1), _T_en(c, 0.9)
        Tp = np.linspace(lo, hi, n) if n > 1 else np.array([_T_en(c, 0.5)])
    lk, Ea = [], []
    for t in Tp:
        e = Ea0 * 1000
        k_pico = e * c.beta / (R * t ** 2)           # condición de máximo en orden 1
        lk.append(math.log10(k_pico * math.exp(-e / R * (1 / T_REF - 1 / t))))
        Ea.append(Ea0)
    return np.array(lk), np.array(Ea)


def ajuste_global(curvas, n=1, orden_libre=False, puntos=200, semilla=None):
    """Ajusta log10 k(T_REF), Ea, fracciones y (opcional) orden de N reacciones paralelas a todas las curvas."""
    fr = friedman(curvas)
    lk0, Ea0 = semilla if semilla is not None else _semilla(curvas, n, fr)
    x0 = list(lk0) + list(Ea0) + [0.0] * (n - 1) + ([1.0] * n if orden_libre else [])
    lo = [-12] * n + [50] * n + [-8] * (n - 1) + ([0.3] * n if orden_libre else [])
    hi = [4] * n + [450] * n + [8] * (n - 1) + ([3.0] * n if orden_libre else [])
    x0 = np.clip(x0, np.array(lo) + 1e-6, np.array(hi) - 1e-6)
    idx = [np.linspace(0, len(c.T) - 1, min(puntos, len(c.T))).astype(int) for c in curvas]

    def resid(x):
        lk, Ea, frac, orden = _desempacar(x, n, orden_libre)
        out = []
        for c, ii in zip(curvas, idx):
            a = simular_alpha(c.T, c.beta, lk, Ea, frac, orden)
            out.append(np.nan_to_num(a[ii] - c.alpha[ii], nan=1.0))
        return np.concatenate(out)

    sol = least_squares(resid, x0, bounds=(lo, hi), x_scale="jac", method="trf")
    lk, Ea, frac, orden = _desempacar(sol.x, n, orden_libre)
    rmse = float(np.sqrt(np.mean(sol.fun ** 2)))
    J = sol.jac
    dof = max(1, len(sol.fun) - len(sol.x))
    try:
        cov = np.linalg.inv(J.T @ J) * (np.sum(sol.fun ** 2) / dof)
        err = np.sqrt(np.clip(np.diag(cov), 0, None))
    except np.linalg.LinAlgError:
        err = np.full(len(sol.x), np.nan)
    comps = []
    for i in range(n):
        e = Ea[i]
        A = 10 ** lk[i] * math.exp(e / (R * T_REF))
        comps.append({
            "fraccion": float(frac[i]), "A_s": A, "log10A": math.log10(A), "Ea_kJ_mol": e / 1000,
            "Ea_err_kJ_mol": float(err[n + i]), "log10k700_err": float(err[i]), "orden": float(orden[i]),
        })
    # en orden de temperatura de reacción: T a la que k = 1e-3 1/s
    comps.sort(key=lambda d: d["Ea_kJ_mol"] * 1000 / (R * (math.log(d["A_s"]) - math.log(1e-3))))
    res = float(np.median([c.residuo for c in curvas]))
    return {"componentes": comps, "rmse_alpha": rmse, "residuo_fraccion": res, "exito": bool(sol.success), "_x": sol.x}


def para_simulador(ajuste, dHr=1.0e6, s=None):
    """Convierte el ajuste en entradas POLY y mezcla para modelo.py / model.js."""
    s = s or {"W": .45, "D": .27, "G": .16, "Gs": .10, "C": .02}
    poly, mix = {}, {}
    for i, c in enumerate(ajuste["componentes"]):
        k = f"TGA{i + 1}"
        poly[k] = {"A": c["A_s"], "Ea": c["Ea_kJ_mol"] * 1000, "s": dict(s), "Tm": 403, "dHm": 150e3, "dHr": dHr}
        mix[k] = c["fraccion"]
    return {"POLY": poly, "mix": mix}


def graficar(curvas, fr, ka, aj, n, orden_libre, carpeta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 3, figsize=(15, 4.5))
    lk, Ea, frac, orden = _desempacar(aj["_x"], n, orden_libre)
    for c in curvas:
        ln, = ax[0].plot(c.T - 273.15, c.alpha, lw=2, label=f"{c.beta * 60:.0f} K/min")
        ax[0].plot(c.T - 273.15, simular_alpha(c.T, c.beta, lk, Ea, frac, orden), "--", color=ln.get_color(), lw=1)
        ax[1].plot(c.T - 273.15, c.dadt / c.beta, color=ln.get_color())
    ax[0].set(xlabel="Temperatura (°C)", ylabel="Conversión α", title=f"Medido (línea) y ajuste global (guiones), RMSE {aj['rmse_alpha']:.4f}")
    ax[0].legend()
    ax[1].set(xlabel="Temperatura (°C)", ylabel="dα/dT (1/K)", title="Velocidad de pérdida de masa (DTG)")
    ax[2].plot([r["alpha"] for r in fr], [r["Ea_kJ_mol"] for r in fr], "o-", label="Friedman")
    ax[2].plot([r["alpha"] for r in ka], [r["Ea_kJ_mol"] for r in ka], "s-", label="KAS")
    for c in aj["componentes"]:
        ax[2].axhline(c["Ea_kJ_mol"], ls=":", color="gray")
    ax[2].set(xlabel="Conversión α", ylabel="Ea (kJ/mol)", title="Energía de activación según la conversión")
    ax[2].legend()
    fig.tight_layout()
    ruta = pathlib.Path(carpeta) / "cinetica_tga.png"
    fig.savefig(ruta, dpi=130)
    plt.close(fig)
    return ruta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--componentes", type=int, default=1, help="reacciones paralelas (≈ plásticos distintos en la mezcla)")
    ap.add_argument("--orden-libre", action="store_true", help="ajustar también el orden de reacción n")
    ap.add_argument("--salida", default="resultados")
    a = ap.parse_args(argv)

    carpeta = pathlib.Path(a.salida)
    carpeta.mkdir(parents=True, exist_ok=True)
    curvas = [preparar(b, T, m) for b, (T, m) in leer_csv(a.csv).items()]
    fr, ka = friedman(curvas), kas(curvas)
    aj = ajuste_global(curvas, a.componentes, a.orden_libre)

    print(f"\nCurvas: {', '.join(f'{c.beta * 60:g}' for c in curvas)} K/min · residuo sólido {aj['residuo_fraccion'] * 100:.1f} %\n")
    print("α     Ea Friedman   Ea KAS   (kJ/mol)")
    for f, k in zip(fr, ka):
        print(f"{f['alpha']:.2f}  {f['Ea_kJ_mol']:8.1f}   {k['Ea_kJ_mol']:8.1f}")
    eas = [r["Ea_kJ_mol"] for r in fr]
    if eas and (max(eas) - min(eas)) / np.mean(eas) > 0.2:
        print("\n⚠ Ea cambia más de 20 % con la conversión: hay varias reacciones. Prueba con --componentes 2 o 3.")
    print(f"\nAjuste global con {a.componentes} componente(s), RMSE en α = {aj['rmse_alpha']:.4f}")
    for i, c in enumerate(aj["componentes"], 1):
        print(f"  {i}. fracción {c['fraccion']:.3f} · Ea {c['Ea_kJ_mol']:.1f} ± {c['Ea_err_kJ_mol']:.1f} kJ/mol · "
              f"A {c['A_s']:.3e} 1/s · orden {c['orden']:.2f}")
    if aj["rmse_alpha"] > 0.02:
        print("⚠ El ajuste deja errores mayores a 0.02 en α: prueba con más componentes o --orden-libre.")

    out = {k: v for k, v in aj.items() if not k.startswith("_")}
    out.update({"friedman": fr, "kas": ka, "velocidades_K_min": [c.beta * 60 for c in curvas],
                "simulador": para_simulador(aj)})
    (carpeta / "cinetica_tga.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    png = graficar(curvas, fr, ka, aj, a.componentes, a.orden_libre, carpeta)
    print(f"\nGuardado: {carpeta / 'cinetica_tga.json'} y {png}")


if __name__ == "__main__":
    main()
