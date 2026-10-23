"""Hoja de cálculo mecánico y de seguridad del reactor de pirólisis.

    uv run python hoja.py                                  # reactor de 300 L del simulador
    uv run python hoja.py --V 1.0 --P 4 --S 95 --potencia 80
    uv run python hoja.py --ayuda-S                        # de dónde sacar el esfuerzo permitido

Cubre:
  1. Espesor de casco y tapas por ASME VIII Div. 1 (UG-27, UG-32), presión máxima de trabajo y prueba hidrostática (UG-99).
  2. Revisión orientativa contra vacío (Windenburg–Trilling).
  3. Válvula de alivio por API 520 Parte I y escenarios de API 521 (salida bloqueada, incendio, falla del N₂).
  4. Transferencia de calor pared → fundido con agitador de ancla (Uhl y Gray): cuánta potencia acepta el reactor.

Todo en SI: m, Pa, K, W, kg. Los esfuerzos se dan en MPa.
"""
import argparse
import math
from dataclasses import dataclass, field

PATM = 101325.0
G = 9.81

# Áreas efectivas de orificio de API 526, mm²
ORIFICIOS_API526 = [("D", 71), ("E", 126), ("F", 198), ("G", 325), ("H", 506), ("J", 830), ("K", 1186),
                    ("L", 1841), ("M", 2323), ("N", 2800), ("P", 4116), ("Q", 7129), ("R", 10323), ("T", 16774)]
LAMINAS_MM = [3, 4, 5, 6, 8, 10, 12, 14, 16, 19, 22, 25]


@dataclass
class Datos:
    V: float = 0.3                # volumen total del recipiente, m³
    H_D: float = 1.5              # altura del casco / diámetro
    llenado: float = 0.6          # fracción del volumen con fundido
    P_diseno_barg: float = 6.0    # presión de diseño, bar manométricos (≥ disparo de la PSV)
    T_diseno_C: float = 550.0     # temperatura de diseño del metal (la pared está más caliente que el fundido)
    S_diseno: float = 80.0        # esfuerzo permitido a T de diseño, MPa — VALOR DE EJEMPLO, verifícalo en ASME II-D
    S_ambiente: float = 115.0     # esfuerzo permitido a temperatura ambiente, MPa — VALOR DE EJEMPLO
    E_junta: float = 0.85         # eficiencia de junta: 1.0 radiografía total, 0.85 por puntos, 0.70 sin radiografía
    CA_mm: float = 3.0            # sobreespesor de corrosión
    E_modulo_GPa: float = 155.0   # módulo de Young del inoxidable a ~550 °C
    rho_acero: float = 8000.0
    # válvula de alivio
    P_disparo_barg: float = 5.0
    potencia_kW: float = 40.0     # potencia máxima del calentador
    dH_kJ_kg: float = 1300.0      # craqueo + vaporización (lo mide la DSC)
    lambda_fuego_kJ_kg: float = 300.0  # calor latente del líquido en incendio (aceite ligero)
    N2_max_kg_h: float = 5.0      # flujo de N₂ si el regulador falla abierto
    M_vapor: float = 113.0        # g/mol, vapor del reactor (mezcla de lumps)
    k_vapor: float = 1.05         # Cp/Cv del vapor de hidrocarburos pesados
    T_alivio_C: float = 480.0
    disco_ruptura: bool = True    # disco antes de la PSV (protege de ceras que la tapen)
    contra_incendio: bool = True  # hay drenaje y bomberos (API 521: 43 200 en vez de 70 900)
    # transferencia de calor
    rpm: float = 30.0
    mu_Pa_s: list = field(default_factory=lambda: [100.0, 10.0, 1.0, 0.1, 0.01])
    k_fundido: float = 0.15       # W/(m·K)
    cp_fundido: float = 2500.0    # J/(kg·K)
    rho_fundido: float = 750.0
    dT_pared_K: float = 100.0     # pared − fundido; más ΔT = más coque pegado y menos resistencia del acero


# ---------- Geometría ----------
def geometria(d):
    """Casco cilíndrico con dos tapas elipsoidales 2:1. Regresa D, longitud del casco, área mojada."""
    # V = π D² L / 4 + 2 · π D³ / 24, con L = H_D · D
    D = (d.V / (math.pi / 4 * d.H_D + math.pi / 12)) ** (1 / 3)
    L = d.H_D * D
    A_tapa = 1.084 * D ** 2
    V_tapa = math.pi * D ** 3 / 24
    V_liq = d.llenado * d.V
    if V_liq <= V_tapa:
        A_moj = A_tapa * V_liq / V_tapa
    else:
        h = min(L, (V_liq - V_tapa) / (math.pi * D ** 2 / 4))
        A_moj = A_tapa + math.pi * D * h
    return {"D": D, "L": L, "A_tapa": A_tapa, "A_mojada": A_moj, "A_total": 2 * A_tapa + math.pi * D * L}


# ---------- ASME VIII Div. 1 ----------
def t_casco(P, R, S, E):
    """UG-27(c)(1), esfuerzo circunferencial. P y S en las mismas unidades; R radio interior."""
    return P * R / (S * E - 0.6 * P)


def t_casco_long(P, R, S, E):
    """UG-27(c)(2), esfuerzo longitudinal."""
    return P * R / (2 * S * E + 0.4 * P)


def t_tapa_eliptica(P, D, S, E):
    """UG-32(d), tapa elipsoidal 2:1."""
    return P * D / (2 * S * E - 0.2 * P)


def mawp_casco(t, R, S, E):
    return S * E * t / (R + 0.6 * t)


def mawp_tapa(t, D, S, E):
    return 2 * S * E * t / (D + 0.2 * t)


def comercial(t_mm):
    return next((x for x in LAMINAS_MM if x >= t_mm), math.ceil(t_mm))


def vacio_windenburg(E, t, D, L):
    """Presión externa de pandeo elástico de un cilindro (Windenburg–Trilling), Pa. Orientativo."""
    nu = 0.3
    return 2.42 * E * (t / D) ** 2.5 / ((1 - nu * nu) ** 0.75 * (L / D - 0.45 * (t / D) ** 0.5))


# ---------- API 520 / 521 ----------
def coef_C(k):
    """Coeficiente de API 520 Parte I (SI) para flujo crítico."""
    return 0.03948 * math.sqrt(k * (2 / (k + 1)) ** ((k + 1) / (k - 1)))


def area_api520(W_kg_h, P1_kPa, T_K, M, k, Z=1.0, Kd=0.975, Kb=1.0, Kc=1.0):
    """Área efectiva requerida, mm² (API 520 Parte I, vapor en flujo crítico)."""
    return W_kg_h / (coef_C(k) * Kd * P1_kPa * Kb * Kc) * math.sqrt(T_K * Z / M)


def calor_incendio(A_mojada, F=1.0, contra_incendio=True):
    """API 521, W. A_mojada en m² hasta 7.6 m sobre el piso."""
    return (43200 if contra_incendio else 70900) * F * A_mojada ** 0.82


def orificio(A_mm2):
    return next(((l, a) for l, a in ORIFICIOS_API526 if a >= A_mm2), ("mayor que T", None))


# ---------- Transferencia de calor ----------
def h_ancla(mu, D, rpm, rho, cp, k):
    """Uhl y Gray para ancla: Nu = 0.36 Re^(2/3) Pr^(1/3), con el diámetro del recipiente."""
    N = rpm / 60
    d_ag = 0.95 * D
    Re = rho * N * d_ag ** 2 / mu
    Pr = cp * mu / k
    Nu = 0.36 * Re ** (2 / 3) * Pr ** (1 / 3)
    return Nu * k / D, Re


# ---------- Hoja completa ----------
def calcular(d):
    g = geometria(d)
    D, R = g["D"], g["D"] / 2
    P = d.P_diseno_barg * 1e5
    S, Sa = d.S_diseno * 1e6, d.S_ambiente * 1e6
    CA = d.CA_mm / 1000
    tc = t_casco(P, R + CA, S, d.E_junta)
    tl = t_casco_long(P, R + CA, S, d.E_junta)
    th = t_tapa_eliptica(P, D + 2 * CA, S, d.E_junta)
    t_min = 1.5e-3  # UG-16(b), sin corrosión
    tc_tot = max(tc, tl, t_min) + CA
    th_tot = max(th, t_min) + CA
    tc_nom, th_nom = comercial(tc_tot * 1000), comercial(th_tot * 1000)
    tcn, thn = tc_nom / 1000 - CA, th_nom / 1000 - CA
    mawp = min(mawp_casco(tcn, R + CA, S, d.E_junta), mawp_tapa(thn, D + 2 * CA, S, d.E_junta))
    p_hidro = 1.3 * mawp * Sa / S
    masa = d.rho_acero * (math.pi * D * g["L"] * tc_nom / 1000 + 2 * g["A_tapa"] * th_nom / 1000)
    p_vac = vacio_windenburg(d.E_modulo_GPa * 1e9, tcn, D, g["L"])

    # Válvula de alivio
    P_set = d.P_disparo_barg * 1e5
    T = d.T_alivio_C + 273.15
    Kc = 0.9 if d.disco_ruptura else 1.0
    esc = []
    W_bloq = d.potencia_kW * 1e3 / (d.dH_kJ_kg * 1e3) * 3600
    esc.append(("Salida bloqueada (condensador tapado con cera)", W_bloq, 1.10, d.M_vapor, d.k_vapor))
    Q_f = calor_incendio(g["A_mojada"], contra_incendio=d.contra_incendio)
    esc.append(("Incendio alrededor del reactor", Q_f / (d.lambda_fuego_kJ_kg * 1e3) * 3600, 1.21, d.M_vapor, d.k_vapor))
    esc.append(("Regulador de N₂ falla abierto", d.N2_max_kg_h, 1.10, 28.0, 1.40))
    filas = []
    for nombre, W, sobre, M, k in esc:
        P1 = (P_set * sobre + PATM) / 1000
        A = area_api520(W, P1, T, M, k, Kc=Kc)
        filas.append({"escenario": nombre, "W_kg_h": W, "P1_kPa": P1, "A_mm2": A})
    rige = max(filas, key=lambda f: f["A_mm2"])
    letra, A_or = orificio(rige["A_mm2"])

    # Calor
    hs = []
    for mu in d.mu_Pa_s:
        h, Re = h_ancla(mu, D, d.rpm, d.rho_fundido, d.cp_fundido, d.k_fundido)
        q = h * d.dT_pared_K
        hs.append({"mu": mu, "Re": Re, "h": h, "q_kW_m2": q / 1000, "P_max_kW": q * g["A_mojada"] / 1000})

    return {"geo": g, "t_casco_calc_mm": max(tc, tl) * 1000, "t_tapa_calc_mm": th * 1000,
            "t_casco_mm": tc_nom, "t_tapa_mm": th_nom, "mawp_barg": mawp / 1e5, "p_hidro_barg": p_hidro / 1e5,
            "masa_acero_kg": masa, "p_vacio_pandeo_bar": p_vac / 1e5, "psv": filas, "rige": rige,
            "orificio": (letra, A_or), "calor": hs, "Q_incendio_kW": Q_f / 1000}


def imprimir(d, r):
    g = r["geo"]
    print(f"\nRecipiente de {d.V * 1000:.0f} L: Ø interior {g['D'] * 1000:.0f} mm, casco {g['L'] * 1000:.0f} mm, tapas elipsoidales 2:1")
    print(f"  Área mojada con {d.llenado * 100:.0f} % de llenado: {g['A_mojada']:.2f} m² (total {g['A_total']:.2f} m²)")

    print(f"\n1. Espesor (ASME VIII Div. 1) a {d.P_diseno_barg:.1f} barg y {d.T_diseno_C:.0f} °C, S = {d.S_diseno:.0f} MPa, E = {d.E_junta}")
    print(f"  Casco: calculado {r['t_casco_calc_mm']:.2f} mm + {d.CA_mm:.0f} mm de corrosión → lámina de {r['t_casco_mm']} mm")
    print(f"  Tapas: calculado {r['t_tapa_calc_mm']:.2f} mm + {d.CA_mm:.0f} mm de corrosión → lámina de {r['t_tapa_mm']} mm")
    print(f"  Presión máxima de trabajo (MAWP) con esas láminas, corroídas: {r['mawp_barg']:.1f} barg")
    print(f"  Prueba hidrostática (UG-99): {r['p_hidro_barg']:.1f} barg")
    print(f"  Masa de acero del casco y tapas: {r['masa_acero_kg']:.0f} kg (sin bridas, boquillas ni soportes)")
    if r["mawp_barg"] < d.P_disparo_barg:
        print("  ⚠ La MAWP queda abajo del disparo de la PSV: sube el espesor o baja el disparo.")
    lim = r["p_vacio_pandeo_bar"] / 3
    print(f"\n2. Vacío: el casco pandearía a {r['p_vacio_pandeo_bar']:.1f} bar de presión externa; con factor 3 aguanta {lim:.2f} bar.")
    if lim < 1.0:
        print("  ⚠ No aguanta vacío total. Al enfriarse, el vapor condensa y puede jalar vacío: pon un rompedor de vacío con N₂ o anillos atiesadores.")
    else:
        print("  Aguanta vacío total (orientativo; ASME usa las gráficas de UG-28).")

    print(f"\n3. Válvula de alivio (API 520/521), disparo {d.P_disparo_barg:.1f} barg, {d.T_alivio_C:.0f} °C"
          + (", con disco de ruptura (Kc 0.9)" if d.disco_ruptura else ""))
    for f in r["psv"]:
        marca = "  ← rige" if f is r["rige"] else ""
        print(f"  {f['escenario']:48s} {f['W_kg_h']:7.1f} kg/h → {f['A_mm2']:7.1f} mm²{marca}")
    letra, A = r["orificio"]
    print(f"  Orificio API 526: {letra}" + (f" ({A} mm²)" if A else "") + f" · calor de incendio {r['Q_incendio_kW']:.0f} kW")

    print(f"\n4. Calor que acepta el fundido por la pared (ancla a {d.rpm:.0f} rpm, ΔT pared–fundido {d.dT_pared_K:.0f} K)")
    print("   viscosidad      Re      h (W/m²K)   flujo (kW/m²)   potencia máx. (kW)")
    for c in r["calor"]:
        nota = "  laminar: correlación extrapolada" if c["Re"] < 300 else ""
        print(f"   {c['mu']:7.2f} Pa·s {c['Re']:9.1f} {c['h']:9.0f} {c['q_kW_m2']:12.1f} {c['P_max_kW']:16.1f}{nota}")
    no_alcanza = [c for c in r["calor"] if c["P_max_kW"] < d.potencia_kW]
    if no_alcanza:
        peor = max(no_alcanza, key=lambda c: c["mu"])
        mejor = min(r["calor"], key=lambda c: c["mu"])
        print(f"  ⚠ La pared no deja pasar los {d.potencia_kW:.0f} kW del calentador: con el plástico recién fundido")
        print(f"    ({peor['mu']:g} Pa·s) entran {peor['P_max_kW']:.0f} kW, y aun con el aceite ya craqueado ({mejor['mu']:g} Pa·s) {mejor['P_max_kW']:.0f} kW.")
        print("    El reactor queda limitado por transferencia de calor, no por cinética. Opciones: más área (serpentín,")
        print("    reactor más esbelto), más ΔT (más coque en la pared) o cargar por etapas sobre aceite caliente.")


AYUDA_S = """
El esfuerzo permitido S sale de ASME Boiler and Pressure Vessel Code, Sección II, Parte D, Tabla 1A,
en la línea de tu material (por ejemplo SA-240 tipo 316, 316H, 310S o 304H) y a tu temperatura de diseño.

- Usa la edición vigente del código y lee las notas de la línea: algunas permiten un valor más alto
  si se acepta una deformación pequeña. Para recipientes con bridas no conviene ese valor.
- Los grados «L» (316L, 304L) tienen un límite de temperatura más bajo en la División 1.
  Para 500–550 °C se usan normalmente 316/316H, 321H o 310S.
- Los valores por defecto de esta hoja (80 MPa a 550 °C y 115 MPa a temperatura ambiente) son de EJEMPLO,
  para ver órdenes de magnitud. No son de la tabla. Pídele al pailero o al inspector la tabla de su edición.
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--V", type=float, default=0.3, help="volumen del reactor, m³")
    ap.add_argument("--P", type=float, default=6.0, help="presión de diseño, barg")
    ap.add_argument("--T", type=float, default=550.0, help="temperatura de diseño del metal, °C")
    ap.add_argument("--S", type=float, default=80.0, help="esfuerzo permitido a T de diseño, MPa")
    ap.add_argument("--S-amb", type=float, default=115.0, help="esfuerzo permitido a temperatura ambiente, MPa")
    ap.add_argument("--E", type=float, default=0.85, help="eficiencia de junta")
    ap.add_argument("--potencia", type=float, default=40.0, help="potencia del calentador, kW")
    ap.add_argument("--disparo", type=float, default=5.0, help="disparo de la PSV, barg")
    ap.add_argument("--llenado", type=float, default=0.6)
    ap.add_argument("--ayuda-S", action="store_true")
    a = ap.parse_args(argv)
    if a.ayuda_S:
        print(AYUDA_S)
        return
    d = Datos(V=a.V, P_diseno_barg=a.P, T_diseno_C=a.T, S_diseno=a.S, S_ambiente=a.S_amb, E_junta=a.E,
              potencia_kW=a.potencia, P_disparo_barg=a.disparo, llenado=a.llenado)
    imprimir(d, calcular(d))
    print("\nS = esfuerzo permitido. Los valores por defecto son de EJEMPLO: corre con --ayuda-S para saber dónde verificarlos.")


if __name__ == "__main__":
    main()
