"""Tren de separación de la pirólisis con Peng–Robinson.

    reactor ──vapor──▶ deflegmador (flash a Td) ──vapor──▶ condensador (flash a Tc) ──gas──▶ antorcha
                          │ líquido                            │ aceite crudo
                          ▼ regresa al reactor                 ▼ corte a 180 °C y 360 °C
                                                          gasolina · diésel · ceras

Uso:
    uv run python diagrama.py                                  # caso base del simulador
    uv run python diagrama.py --Td 300 --P 2.5 --Tc 20         # cambia condiciones
    uv run python diagrama.py --dwsim resultados/receta_dwsim.md

Además compara con las reglas simples del simulador web (Clausius–Clapeyron + Trouton),
para saber cuánto se equivocan.
"""
import argparse
import json
import math
import pathlib

import numpy as np

import componentes as cm
from pr import PR, h_ideal_masa

R = 8.314462618
NOMBRE_LUMP = {"G": "gasolina", "D": "diésel", "W": "ceras", "gas": "gas C1–C4", "N2": "nitrógeno"}

# Vapor que sale del reactor antes del deflegmador (caso base del simulador a 460 °C, % masa)
CASO_BASE = {"flujo_kg_h": 15.0, "T_C": 460.0, "P_bar": 1.2, "n2_mol_s": 0.005,
             "lumps": {"W": 0.20, "D": 0.42, "G": 0.26, "gas": 0.12}}


class Tren:
    def __init__(self, K=12.5, gas=None):
        self.ps = cm.pseudos_por_lump(K)
        gas = gas or cm.GAS_TIPICO
        self.gas_frac = {k: v / sum(gas.values()) for k, v in gas.items()}
        self.comps = [cm.PUROS["N2"]] + [cm.PUROS[k] for k in self.gas_frac] + [p for l in "GDW" for p in self.ps[l]]
        self.lump = ["N2"] + ["gas"] * len(self.gas_frac) + [l for l in "GDW" for _ in self.ps[l]]
        self.Tb = np.array([c.Tb for c in self.comps])
        self.pr = PR(self.comps)
        self.M = self.pr.M

    def alimentacion(self, caso):
        """Flujos molares (mol/s) a partir de kg/h por lump y la purga de N2."""
        m = caso["flujo_kg_h"] / 3600
        n = np.zeros(len(self.comps))
        n[0] = caso["n2_mol_s"]
        i = 1
        for k, f in self.gas_frac.items():
            n[i] = m * caso["lumps"]["gas"] * f / self.M[i]
            i += 1
        for l in "GDW":
            for _ in self.ps[l]:
                n[i] = m * caso["lumps"][l] / len(self.ps[l]) / self.M[i]
                i += 1
        return n

    def flash(self, n, T, P):
        N = n.sum()
        V, x, y = self.pr.flash(n / N, T, P)
        return N * V * y, N * (1 - V) * x

    def entalpia(self, n, T, P):
        """W (J/s) relativa a gas ideal a 25 °C."""
        if n.sum() <= 0:
            return 0.0
        nv, nl = self.flash(n, T, P)
        h = (n * self.M).sum() * h_ideal_masa(T)
        if nv.sum() > 1e-12:
            h += nv.sum() * self.pr.h_residual(nv, T, P, "V")
        if nl.sum() > 1e-12:
            h += nl.sum() * self.pr.h_residual(nl, T, P, "L")
        return h

    def por_lump(self, n):
        kg = n * self.M * 3600
        return {l: float(kg[[i for i, x in enumerate(self.lump) if x == l]].sum()) for l in ("G", "D", "W", "gas", "N2")}


def regla_simple(Tb, T, P):
    """La regla del simulador web: P_sat por Trouton."""
    return 101325 * math.exp(min(40, 88 / 8.314 * (1 - Tb / T)))


def flash_simulador(caso, Td, P):
    """La regla del deflegmador del simulador web (flash ideal de 3 lumps con Trouton), para comparar."""
    from scipy.optimize import brentq
    m, L = caso["flujo_kg_h"] / 3600, caso["lumps"]
    M, Tb = {"W": .45, "D": .23, "G": .10}, {"W": 780, "D": 560, "G": 400}
    n = {k: m * L[k] / M[k] for k in M}
    nnc = m * L["gas"] / 0.03 + caso["n2_mol_s"]
    N = nnc + sum(n.values())
    K = {k: regla_simple(Tb[k], Td, P) / P for k in M}
    f = lambda V: nnc / N / V + sum(n[k] / N * (K[k] - 1) / ((1 - V) + V * K[k]) for k in M)
    if f(1.0) >= 0:
        return {k: 0.0 for k in M}
    V = brentq(f, 1e-9, 1.0)
    return {k: (1 - V) / ((1 - V) + V * K[k]) for k in M}


def correr(caso, Td_C, Tc_C, T_agua=(20.0, 30.0), corte_G=216.0, corte_D=369.0, reflujo=True, tren=None):
    """Cortes por defecto en el Tb del n-C12 y del n-C22, para que coincidan con los lumps del simulador."""
    t = tren or Tren()
    P = caso["P_bar"] * 1e5
    Tr, Td, Tc = caso["T_C"] + 273.15, Td_C + 273.15, Tc_C + 273.15
    n0 = t.alimentacion(caso)
    H0 = t.entalpia(n0, Tr, P)
    res = {"P_bar": caso["P_bar"], "T_reactor_C": caso["T_C"], "T_defleg_C": Td_C if reflujo else None, "T_cond_C": Tc_C}

    if reflujo:
        nv, nl = t.flash(n0, Td, P)
        Q_d = H0 - t.entalpia(nv, Td, P) - t.entalpia(nl, Td, P)
    else:
        nv, nl, Q_d = n0, np.zeros_like(n0), 0.0
    ent = t.por_lump(n0)
    ret = t.por_lump(nl)
    res["deflegmador"] = {
        "calor_retirado_kW": Q_d / 1000,
        "regresa_kg_h": ret,
        "fraccion_que_regresa": {l: (ret[l] / ent[l] if ent[l] > 0 else 0.0) for l in ("W", "D", "G")},
    }

    gas, aceite = t.flash(nv, Tc, P)
    Q_c = t.entalpia(nv, Td if reflujo else Tr, P) - t.entalpia(gas, Tc, P) - t.entalpia(aceite, Tc, P)
    agua = Q_c / (4186 * (T_agua[1] - T_agua[0]))
    res["condensador"] = {
        "calor_kW": Q_c / 1000, "agua_kg_h": agua * 3600, "agua_L_min": agua * 60,
        "gas_kg_h": t.por_lump(gas), "aceite_kg_h": t.por_lump(aceite),
    }
    perdida_G = t.por_lump(gas)["G"]
    entra_G = t.por_lump(nv)["G"]
    res["condensador"]["gasolina_perdida_en_gas_pct"] = 100 * perdida_G / entra_G if entra_G > 0 else 0.0

    # Corte ideal del aceite por punto de ebullición
    kg = aceite * t.M * 3600
    ligeros = np.array([l in ("gas", "N2") for l in t.lump])
    Tb_C = t.Tb - 273.15
    sel_G = (~ligeros) & (Tb_C < corte_G)
    sel_D = (~ligeros) & (Tb_C >= corte_G) & (Tb_C < corte_D)
    sel_W = (~ligeros) & (Tb_C >= corte_D)
    res["aceite"] = {
        "kg_h": float(kg.sum()), "gas_disuelto_pct": float(100 * kg[ligeros].sum() / kg.sum()),
        "gasolina_kg_h": float(kg[sel_G].sum()), "diesel_kg_h": float(kg[sel_D].sum()), "ceras_kg_h": float(kg[sel_W].sum()),
    }

    # Presión de vapor verdadera de la gasolina a 37.8 °C, con y sin el gas disuelto
    T38 = 310.93
    con_gas = aceite * (sel_G | ligeros)
    sin_gas = aceite * sel_G
    res["calidad"] = {
        "PVV_gasolina_con_gas_kPa": t.pr.p_burbuja(con_gas, T38) / 1000 if con_gas.sum() > 0 else None,
        "PVV_gasolina_estabilizada_kPa": t.pr.p_burbuja(sin_gas, T38) / 1000 if sin_gas.sum() > 0 else None,
    }

    # Comparación con las reglas simples del simulador
    sim = flash_simulador(caso, Td, P) if reflujo else {"W": 0.0, "D": 0.0, "G": 0.0}
    n_nc = (gas[[i for i, x in enumerate(t.lump) if x in ("gas", "N2")]]).sum()
    PsG = regla_simple(400, Tc, P)
    perd_sim = n_nc * PsG / (P - PsG) * 0.10 * 3600
    res["simulador_web"] = {"fraccion_que_regresa": sim,
                            "gasolina_perdida_en_gas_pct": 100 * min(1.0, perd_sim / entra_G) if entra_G > 0 else 0.0}
    res["_tren"] = t
    return res


def imprimir(r):
    d, c, a, q, s = r["deflegmador"], r["condensador"], r["aceite"], r["calidad"], r["simulador_web"]
    print(f"\nReactor {r['T_reactor_C']:.0f} °C · {r['P_bar']:.2f} bar abs")
    if r["T_defleg_C"] is not None:
        print(f"\nDeflegmador a {r['T_defleg_C']:.0f} °C: retira {d['calor_retirado_kW']:.2f} kW")
        print("  Fracción que regresa al reactor   Peng–Robinson   regla del simulador")
        for l in ("W", "D", "G"):
            print(f"    {NOMBRE_LUMP[l]:10s}                       {d['fraccion_que_regresa'][l] * 100:5.1f} %         {s['fraccion_que_regresa'][l] * 100:5.1f} %")
    print(f"\nCondensador a {r['T_cond_C']:.0f} °C: {c['calor_kW']:.2f} kW → {c['agua_L_min']:.1f} L/min de agua (20→30 °C)")
    print(f"  Gasolina que se escapa con el gas: {c['gasolina_perdida_en_gas_pct']:.1f} % "
          f"(el simulador estima {s['gasolina_perdida_en_gas_pct']:.1f} %)")
    g = c["gas_kg_h"]
    print(f"  Gas a la antorcha: {g['gas'] + g['G']:.2f} kg/h de hidrocarburo + {g['N2']:.2f} kg/h de N₂")
    print(f"\nAceite crudo: {a['kg_h']:.2f} kg/h · {a['gas_disuelto_pct']:.1f} % es gas C1–C4 disuelto")
    print(f"  Corte a 216/369 °C (n-C12 / n-C22): gasolina {a['gasolina_kg_h']:.2f} · diésel {a['diesel_kg_h']:.2f} · ceras {a['ceras_kg_h']:.2f} kg/h")
    if q["PVV_gasolina_con_gas_kPa"]:
        print(f"\nPresión de vapor verdadera de la gasolina a 37.8 °C:")
        print(f"  con el gas disuelto {q['PVV_gasolina_con_gas_kPa']:.0f} kPa · estabilizada {q['PVV_gasolina_estabilizada_kPa']:.0f} kPa")
        print("  Compárala con el límite de presión de vapor de la NOM-016-CRE-2016 para tu zona y temporada.")
        if q["PVV_gasolina_con_gas_kPa"] > 1.5 * q["PVV_gasolina_estabilizada_kPa"]:
            print("  ⚠ El gas disuelto sube mucho la presión de vapor: hace falta una columna estabilizadora (debutanizadora).")


def receta_dwsim(r, ruta, caso):
    """Escribe en Markdown la receta para armar el mismo diagrama en DWSIM."""
    t = r["_tren"]
    lin = ["# Receta para DWSIM: tren de separación de la pirólisis", "",
           "Generada por `diagrama.py`. Arma esto en DWSIM (Mac, Windows o Linux, gratis en dwsim.org) y compara con los números de abajo.", "",
           "## 1. Paquete de propiedades", "", "Peng–Robinson (PR). k_ij = 0.08 entre N₂ o H₂ y los hidrocarburos; los demás en 0.", "",
           "## 2. Compuestos", "", "Del banco de datos de DWSIM:", ""]
    for c in t.comps:
        if c.SG == 0:
            lin.append(f"- {c.nombre_dwsim} ({c.nombre})")
    lin += ["", "Pseudocomponentes: Herramientas → Caracterización de petróleo → «Hipotéticos» con estos datos "
            "(o captura tu destilación simulada en «Petroleum Assay Manager» y deja que DWSIM los genere):", "",
            "| Nombre | Tb (°C) | SG | M (g/mol) | Tc (°C) | Pc (bar) | ω |", "|---|---|---|---|---|---|---|"]
    for c in t.comps:
        if c.SG > 0:
            lin.append(f"| {c.nombre} | {c.Tb - 273.15:.1f} | {c.SG:.4f} | {c.M * 1000:.1f} | {c.Tc - 273.15:.1f} | {c.Pc / 1e5:.2f} | {c.w:.4f} |")
    n0 = t.alimentacion(caso)
    lin += ["", "## 3. Corriente de alimentación «Vapor del reactor»", "",
            f"T = {r['T_reactor_C']:.0f} °C, P = {r['P_bar']:.2f} bar abs. Flujos molares:", "", "| Compuesto | mol/h | kg/h |", "|---|---|---|"]
    for c, ni in zip(t.comps, n0):
        lin.append(f"| {c.nombre} | {ni * 3600:.3f} | {ni * c.M * 3600:.4f} |")
    lin += ["", "## 4. Equipos", "",
            f"1. **Deflegmador:** «Separador gas–líquido» con especificación de temperatura {r['T_defleg_C']} °C y misma presión. "
            "Su líquido es el reflujo al reactor.",
            f"2. **Condensador:** «Enfriador» a {r['T_cond_C']:.0f} °C seguido de un «Separador gas–líquido». El vapor va a la antorcha y el líquido es el aceite crudo.",
            "3. **Destilación:** «Columna corta (Shortcut)» con clave ligera la primera fracción arriba de 180 °C y clave pesada la última abajo, "
            "o una columna rigurosa si quieres los productos con especificación real.", "",
            "## 5. Resultados de referencia (Peng–Robinson en Python)", "",
            f"- Deflegmador: retira {r['deflegmador']['calor_retirado_kW']:.2f} kW; regresa "
            + ", ".join(f"{NOMBRE_LUMP[l]} {v * 100:.1f} %" for l, v in r['deflegmador']['fraccion_que_regresa'].items()),
            f"- Condensador: {r['condensador']['calor_kW']:.2f} kW; gasolina perdida en el gas {r['condensador']['gasolina_perdida_en_gas_pct']:.1f} %",
            f"- Aceite: {r['aceite']['kg_h']:.2f} kg/h con {r['aceite']['gas_disuelto_pct']:.1f} % de gas disuelto", "",
            "DWSIM debe dar lo mismo con una diferencia de pocos por ciento (usa sus propias correlaciones para Cp de gas ideal)."]
    pathlib.Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(ruta).write_text("\n".join(lin) + "\n", encoding="utf-8")



def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--T", type=float, default=CASO_BASE["T_C"], help="temperatura del reactor, °C")
    ap.add_argument("--P", type=float, default=CASO_BASE["P_bar"], help="presión, bar abs")
    ap.add_argument("--Td", type=float, default=280.0, help="temperatura del deflegmador, °C")
    ap.add_argument("--sin-reflujo", action="store_true")
    ap.add_argument("--Tc", type=float, default=30.0, help="salida del condensador, °C")
    ap.add_argument("--flujo", type=float, default=CASO_BASE["flujo_kg_h"], help="vapor del reactor, kg/h")
    ap.add_argument("--json", help="guardar resultados en JSON")
    ap.add_argument("--dwsim", help="escribir la receta de DWSIM en este archivo .md")
    a = ap.parse_args(argv)
    caso = dict(CASO_BASE, T_C=a.T, P_bar=a.P, flujo_kg_h=a.flujo)
    r = correr(caso, a.Td, a.Tc, reflujo=not a.sin_reflujo)
    imprimir(r)
    if a.json:
        pathlib.Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.json).write_text(json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, indent=2, ensure_ascii=False))
    if a.dwsim:
        receta_dwsim(r, a.dwsim, caso)
        print(f"\nReceta de DWSIM: {a.dwsim}")


if __name__ == "__main__":
    main()
