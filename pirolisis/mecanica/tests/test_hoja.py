"""Fórmulas contra ejemplos resueltos y propiedades que deben cumplirse."""
import math

import pytest

import hoja as h


def test_ug27_ejemplo_a_mano():
    # P = 1.5 MPa, R = 500 mm, S = 138 MPa, E = 1 → 1.5·500 / (138 − 0.9) = 5.471 mm
    assert h.t_casco(1.5, 500, 138, 1.0) == pytest.approx(5.471, abs=1e-3)


def test_mawp_es_la_inversa_del_espesor():
    t = h.t_casco(0.6e6, 0.3, 80e6, 0.85)
    assert h.mawp_casco(t, 0.3, 80e6, 0.85) == pytest.approx(0.6e6, rel=1e-12)
    t = h.t_tapa_eliptica(0.6e6, 0.6, 80e6, 0.85)
    assert h.mawp_tapa(t, 0.6, 80e6, 0.85) == pytest.approx(0.6e6, rel=1e-12)


def test_api520_ejemplo_del_estandar():
    # API 520 Parte I, ejemplo de vapor: 24 270 kg/h, 670 kPa, 348 K, Z 0.9, M 51, k 1.11 → 3 698 mm²
    assert h.area_api520(24270, 670, 348, 51, 1.11, Z=0.9) == pytest.approx(3698, rel=0.003)


def test_coeficiente_C_para_aire():
    assert h.coef_C(1.4) == pytest.approx(0.0270, abs=1e-4)


def test_calor_de_incendio_api521():
    assert h.calor_incendio(10.0) == pytest.approx(43200 * 10 ** 0.82)
    assert h.calor_incendio(10.0, contra_incendio=False) > h.calor_incendio(10.0)


def test_orificio_es_el_siguiente_mas_grande():
    assert h.orificio(100) == ("E", 126)
    assert h.orificio(126) == ("E", 126)
    assert h.orificio(20000)[0] == "mayor que T"


def test_geometria_recupera_el_volumen():
    d = h.Datos(V=0.3)
    g = h.geometria(d)
    V = math.pi * g["D"] ** 2 / 4 * g["L"] + 2 * math.pi * g["D"] ** 3 / 24
    assert V == pytest.approx(0.3, rel=1e-12)
    assert 0 < g["A_mojada"] < g["A_total"]


def test_hoja_completa_es_consistente():
    r = h.calcular(h.Datos())
    assert r["mawp_barg"] >= 6.0          # la lámina comercial no puede quedar abajo de la presión de diseño
    assert r["t_casco_mm"] in h.LAMINAS_MM
    assert r["rige"]["A_mm2"] == max(f["A_mm2"] for f in r["psv"])
    assert all(a["P_max_kW"] < b["P_max_kW"] for a, b in zip(r["calor"], r["calor"][1:]))  # menos viscoso, más calor


def test_mas_esfuerzo_permitido_menos_espesor():
    a = h.calcular(h.Datos(S_diseno=60))["t_casco_calc_mm"]
    b = h.calcular(h.Datos(S_diseno=120))["t_casco_calc_mm"]
    assert b < a
