"""El tren de separación conserva la masa y la regla del simulador web no se aleja de Peng–Robinson."""
import pytest

import diagrama as d


@pytest.fixture(scope="module")
def tren():
    return d.Tren()


def _total(dic):
    return sum(dic.values())


@pytest.mark.parametrize("Td", [260, 280, 300])
def test_masa_que_entra_es_igual_a_la_que_sale(tren, Td):
    r = d.correr(d.CASO_BASE, Td, 30, tren=tren)
    entra = d.CASO_BASE["flujo_kg_h"] + d.CASO_BASE["n2_mol_s"] * 0.028014 * 3600
    sale = _total(r["deflegmador"]["regresa_kg_h"]) + _total(r["condensador"]["gas_kg_h"]) + _total(r["condensador"]["aceite_kg_h"])
    assert sale == pytest.approx(entra, rel=1e-8)


def test_los_dos_equipos_retiran_calor(tren):
    r = d.correr(d.CASO_BASE, 280, 30, tren=tren)
    assert r["deflegmador"]["calor_retirado_kW"] > 0
    assert r["condensador"]["calor_kW"] > 0


@pytest.mark.parametrize("Td", [260, 280, 300, 330])
def test_regla_del_simulador_para_ceras_cerca_de_peng_robinson(tren, Td):
    r = d.correr(d.CASO_BASE, Td, 30, tren=tren)
    pr, sim = r["deflegmador"]["fraccion_que_regresa"]["W"], r["simulador_web"]["fraccion_que_regresa"]["W"]
    assert sim == pytest.approx(pr, abs=0.06)


def test_mas_presion_y_agua_mas_fria_recuperan_mas_gasolina(tren):
    base = d.correr(d.CASO_BASE, 280, 30, tren=tren)["condensador"]["gasolina_perdida_en_gas_pct"]
    frio = d.correr(d.CASO_BASE, 280, 10, tren=tren)["condensador"]["gasolina_perdida_en_gas_pct"]
    alta = d.correr(dict(d.CASO_BASE, P_bar=3.0), 280, 30, tren=tren)["condensador"]["gasolina_perdida_en_gas_pct"]
    assert frio < base and alta < base


def test_el_gas_disuelto_sube_la_presion_de_vapor(tren):
    q = d.correr(d.CASO_BASE, 280, 30, tren=tren)["calidad"]
    assert q["PVV_gasolina_con_gas_kPa"] > q["PVV_gasolina_estabilizada_kPa"]


def test_receta_dwsim_trae_todos_los_compuestos(tmp_path, tren):
    r = d.correr(d.CASO_BASE, 280, 30, tren=tren)
    ruta = tmp_path / "receta.md"
    d.receta_dwsim(r, ruta, d.CASO_BASE)
    texto = ruta.read_text()
    for c in tren.comps:
        assert c.nombre in texto
