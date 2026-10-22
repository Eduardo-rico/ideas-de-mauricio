"""Genera datos sintéticos con parámetros conocidos para comprobar que el ajuste los recupera.

    uv run python generar_datos_prueba.py ejemplo/

Escribe ejemplo/tga_sintetico.csv (mezcla PEAD + PP + PS) y ejemplo/banco_sintetico.csv.
"""
import csv
import pathlib
import sys

import numpy as np

import modelo
from ajuste_banco import config_de_fila
from cinetica_tga import R, T_REF, simular_alpha

# Parámetros "verdaderos" de la TGA: PEAD, PP y PS de la página
VERDAD_TGA = [
    {"nombre": "PEAD", "A": 1.0e16, "Ea": 268e3, "fraccion": 0.5},
    {"nombre": "PP", "A": 1.9e13, "Ea": 220e3, "fraccion": 0.35},
    {"nombre": "PS", "A": 3.0e12, "Ea": 200e3, "fraccion": 0.15},
]
RESIDUO = 0.02


def tga(componentes=VERDAD_TGA, velocidades=(5, 10, 20, 40), ruido_pct=0.05, semilla=1):
    """Filas (velocidad_K_min, temperatura_C, masa_%) de una TGA simulada con ruido gaussiano."""
    rng = np.random.default_rng(semilla)
    lk = [np.log10(c["A"] * np.exp(-c["Ea"] / (R * T_REF))) for c in componentes]
    Ea = [c["Ea"] for c in componentes]
    frac = [c["fraccion"] for c in componentes]
    filas = []
    for v in velocidades:
        T = np.arange(30.0, 650.0, 0.5) + 273.15
        a = simular_alpha(T, v / 60.0, lk, Ea, frac, [1.0] * len(Ea))
        m = 100 * (1 - (1 - RESIDUO) * a) + rng.normal(0, ruido_pct, len(T))
        filas += [(v, round(t - 273.15, 2), round(x, 4)) for t, x in zip(T, m)]
    return filas


# Corridas de banco: 3 kg en un reactor de 10 L
VERDAD_S = {"W": .40, "D": .30, "G": .18, "Gs": .09, "C": .03}
VERDAD_SEC_MULT = {"W": 2.0, "D": 0.5, "G": 1.5}
DISENO_BANCO = [
    {"corrida": "B1", "T_C": 440, "P_bar": 1.2, "reflujo": "si", "T_defleg_C": 330},
    {"corrida": "B2", "T_C": 460, "P_bar": 1.2, "reflujo": "si", "T_defleg_C": 330},
    {"corrida": "B3", "T_C": 480, "P_bar": 1.2, "reflujo": "si", "T_defleg_C": 330},
    {"corrida": "B4", "T_C": 460, "P_bar": 1.2, "reflujo": "no", "T_defleg_C": 330},
    {"corrida": "B5", "T_C": 460, "P_bar": 2.5, "reflujo": "si", "T_defleg_C": 330},
    {"corrida": "B6", "T_C": 460, "P_bar": 1.2, "reflujo": "si", "T_defleg_C": 270},
]


VALIDACION_BANCO = [
    {"corrida": "V1", "T_C": 470, "P_bar": 1.8, "reflujo": "si", "T_defleg_C": 300},
    {"corrida": "V2", "T_C": 450, "P_bar": 1.5, "reflujo": "no", "T_defleg_C": 330},
]
# La mezcla del banco es la misma de la TGA: un pseudo-polímero por componente,
# en el orden en que cinetica_tga.py los nombra (de menor a mayor temperatura de reacción)
MIX_BANCO = {"TGA1": 0.15, "TGA2": 0.35, "TGA3": 0.50}


def parametros_verdaderos():
    p = modelo.parametros()
    por_nombre = {c["nombre"]: c for c in VERDAD_TGA}
    p["POLY"] = {k: {"A": por_nombre[n]["A"], "Ea": por_nombre[n]["Ea"], "s": dict(VERDAD_S), "Tm": 403,
                     "dHm": 150e3, "dHr": 1.0e6} for k, n in zip(MIX_BANCO, ["PS", "PP", "PEAD"])}
    for i, f in VERDAD_SEC_MULT.items():
        p["SEC"][i]["A"] *= f
    return p


def banco(diseno=DISENO_BANCO, ruido_pct=1.0, semilla=2, p=None):
    rng = np.random.default_rng(semilla)
    p = p or parametros_verdaderos()
    filas = []
    for d in diseno:
        fila = {"corrida": d["corrida"], "masa_kg": 3.0, "volumen_m3": 0.01, "T_C": d["T_C"], "P_bar": d["P_bar"],
                "reflujo": d["reflujo"], "T_defleg_C": d["T_defleg_C"], "T_cond_C": 20, "n2_mol_s": 0.0005,
                "catalizador": "none", "carga_cat": 0}
        r = modelo.simular(config_de_fila(fila, MIX_BANCO), p, dt=1.0)
        for col, k in (("gasolina_kg", "G"), ("diesel_kg", "D"), ("ceras_kg", "W"), ("gas_kg", "gas"), ("coque_kg", "char")):
            fila[col] = round(max(0.0, r[k] + rng.normal(0, ruido_pct / 100 * fila["masa_kg"])), 4)
        filas.append(fila)
    return filas


def main(carpeta="ejemplo"):
    c = pathlib.Path(carpeta)
    c.mkdir(parents=True, exist_ok=True)
    with open(c / "tga_sintetico.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["velocidad_K_min", "temperatura_C", "masa"])
        w.writerows(tga())
    for nombre, diseno, sem in (("banco_sintetico.csv", DISENO_BANCO, 2), ("banco_validacion.csv", VALIDACION_BANCO, 3)):
        filas = banco(diseno, semilla=sem)
        with open(c / nombre, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0]))
            w.writeheader()
            w.writerows(filas)
    print(f"Escrito en {c}/: tga_sintetico.csv, banco_sintetico.csv, banco_validacion.csv")


if __name__ == "__main__":
    main(*sys.argv[1:])
