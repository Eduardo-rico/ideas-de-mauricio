"""Componentes puros del gas y pseudocomponentes del aceite de pirólisis.

Correlaciones (Riazi, *Characterization and Properties of Petroleum Fractions*, ASTM MNL50, 2005):
- Peso molecular, Tc y Pc: Riazi–Daubert (1987), válidas para Tb de 300 a 850 K.
- Factor acéntrico: Lee–Kesler (θ = Tb/Tc < 0.8) y Kesler–Lee (θ ≥ 0.8).
- Densidad relativa a partir del factor de Watson K = (1.8 Tb)^(1/3) / SG.
"""
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Componente:
    nombre: str
    Tc: float      # K
    Pc: float      # Pa
    w: float       # factor acéntrico
    M: float       # kg/mol
    Tb: float = 0.0  # K, punto de ebullición normal
    SG: float = 0.0  # densidad relativa 15.6/15.6 °C
    nombre_dwsim: str = ""


def _pc(nombre, Tc, Pc_bar, w, M_g, Tb, dw):
    return Componente(nombre, Tc, Pc_bar * 1e5, w, M_g / 1000, Tb, 0.0, dw)


# Constantes críticas: Poling, Prausnitz y O'Connell, *The Properties of Gases and Liquids*, 5.ª ed.
PUROS = {
    "N2":    _pc("Nitrógeno", 126.20, 33.98, 0.037, 28.014, 77.35, "Nitrogen"),
    "H2":    _pc("Hidrógeno", 33.19, 13.13, -0.216, 2.016, 20.28, "Hydrogen"),
    "CH4":   _pc("Metano", 190.56, 45.99, 0.011, 16.043, 111.66, "Methane"),
    "C2H4":  _pc("Etileno", 282.34, 50.41, 0.087, 28.054, 169.42, "Ethylene"),
    "C2H6":  _pc("Etano", 305.32, 48.72, 0.099, 30.069, 184.55, "Ethane"),
    "C3H6":  _pc("Propileno", 364.85, 46.00, 0.142, 42.081, 225.46, "Propylene"),
    "C3H8":  _pc("Propano", 369.83, 42.48, 0.152, 44.097, 231.02, "Propane"),
    "C4H8":  _pc("1-Buteno", 419.50, 40.20, 0.194, 56.107, 266.92, "1-Butene"),
    "C4H10": _pc("n-Butano", 425.12, 37.96, 0.200, 58.123, 272.66, "N-butane"),
    "nC6":   _pc("n-Hexano", 507.60, 30.25, 0.301, 86.177, 341.88, "N-hexane"),
}

# Gas de pirólisis de poliolefinas, % en masa (composición típica; reemplázala con tu cromatografía)
GAS_TIPICO = {"H2": 1, "CH4": 15, "C2H4": 15, "C2H6": 14, "C3H6": 25, "C3H8": 10, "C4H8": 13, "C4H10": 7}


def sg_watson(Tb, K=12.5):
    """Densidad relativa con factor de Watson K. Aceite de poliolefinas: K ≈ 12.2–12.6 (parafínico-olefínico)."""
    return (1.8 * Tb) ** (1 / 3) / K


def riazi_daubert(Tb, SG):
    """Peso molecular (g/mol), Tc (K) y Pc (bar) de una fracción con Tb (K) y SG."""
    M = 42.965 * math.exp(2.097e-4 * Tb - 7.78712 * SG + 2.08476e-3 * Tb * SG) * Tb ** 1.26007 * SG ** 4.98308
    Tc = 9.5233 * math.exp(-9.314e-4 * Tb - 0.544442 * SG + 6.4791e-4 * Tb * SG) * Tb ** 0.81067 * SG ** 0.53691
    Pc = 3.1958e5 * math.exp(-8.505e-3 * Tb - 4.8014 * SG + 5.749e-3 * Tb * SG) * Tb ** -0.4844 * SG ** 4.0846
    return M, Tc, Pc


def acentrico(Tb, Tc, Pc_bar, SG):
    th = Tb / Tc
    if th < 0.8:
        return ((-math.log(Pc_bar / 1.01325) - 5.92714 + 6.09648 / th + 1.28862 * math.log(th) - 0.169347 * th ** 6)
                / (15.2518 - 15.6875 / th - 13.4721 * math.log(th) + 0.43577 * th ** 6))
    K = (1.8 * Tb) ** (1 / 3) / SG
    return -7.904 + 0.1352 * K - 0.007465 * K * K + 8.359 * th + (1.408 - 0.01063 * K) / th


def pseudo(nombre, Tb, SG=None, K=12.5):
    SG = SG if SG is not None else sg_watson(Tb, K)
    M, Tc, Pc = riazi_daubert(Tb, SG)
    return Componente(nombre, Tc, Pc * 1e5, acentrico(Tb, Tc, Pc, SG), M / 1000, Tb, SG, nombre)


# Pseudocomponentes por grupo de carbonos, con el Tb de la n-parafina representativa (K)
CORTES = {
    "G": [("C5-C6", 325.6), ("C7-C8", 385.2), ("C9-C10", 435.6), ("C11-C12", 479.3)],
    "D": [("C13-C14", 517.7), ("C15-C16", 551.9), ("C17-C18", 582.6), ("C19-C22", 622.9)],
    "W": [("C23-C27", 675.1), ("C28-C32", 722.9), ("C33-C40", 770.0)],
}


def pseudos_por_lump(K=12.5):
    """{lump: [Componente, ...]} con masa repartida por igual dentro de cada lump."""
    return {l: [pseudo(n, tb, K=K) for n, tb in cortes] for l, cortes in CORTES.items()}


def pseudos_de_destilacion(curva, n=12, K=12.5):
    """Pseudocomponentes a partir de una destilación simulada (ASTM D2887).

    curva: lista de (porcentaje_masa_destilado, temperatura_C) creciente.
    Regresa [(Componente, fraccion_masa)] con n cortes de igual masa.
    """
    pts = sorted(curva)
    xs, ts = [p[0] for p in pts], [p[1] + 273.15 for p in pts]

    def T_en(x):
        for i in range(1, len(xs)):
            if x <= xs[i]:
                return ts[i - 1] + (ts[i] - ts[i - 1]) * (x - xs[i - 1]) / (xs[i] - xs[i - 1])
        return ts[-1]

    lo, hi = xs[0], xs[-1]
    paso = (hi - lo) / n
    out = []
    for k in range(n):
        Tb = T_en(lo + (k + 0.5) * paso)
        out.append((pseudo(f"NBP{Tb - 273.15:.0f}", Tb, K=K), paso / (hi - lo)))
    return out
