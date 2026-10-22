"""El ajuste de banco debe recuperar selectividades y predecir corridas que no vio."""
import math

import numpy as np
import pytest

import ajuste_banco as ab
import generar_datos_prueba as gen
import modelo


def _filas(diseno, ruido, semilla):
    filas = gen.banco(diseno, ruido_pct=ruido, semilla=semilla)
    for f in filas:
        f["_medido"] = {k: f[col] for col, k in ab.PRODUCTOS}
    return filas


@pytest.fixture(scope="module")
def ajuste():
    verdad = gen.parametros_verdaderos()
    poly = {k: dict(v, s={"W": .45, "D": .27, "G": .16, "Gs": .10, "C": .02}) for k, v in verdad["POLY"].items()}
    aj = ab.Ajustador(_filas(gen.DISENO_BANCO, 0.3, 5), poly, gen.MIX_BANCO)
    sol, err, corr, rmse = aj.ajustar()
    yield aj, sol, err, rmse, verdad
    aj.cerrar()


def test_recupera_selectividades(ajuste):
    aj, sol, *_ = ajuste
    s = ab._softmax(np.asarray(sol.x[:4]))
    for k, v in zip(ab.S_KEYS, s):
        assert v == pytest.approx(gen.VERDAD_S[k], abs=0.03), k


def test_recupera_craqueo_de_ceras(ajuste):
    aj, sol, err, rmse, verdad = ajuste
    q = verdad["SEC"]["W"]
    k_verdad = q["A"] * math.exp(-q["Ea"] / (modelo.R * ab.T_REF_SEC))
    assert 10 ** sol.x[4] == pytest.approx(k_verdad, rel=0.3)


def test_el_error_del_ajuste_es_del_tamano_del_ruido(ajuste):
    *_, rmse, _ = ajuste
    assert rmse < 0.006  # ruido de 0.3 % de la carga


def test_predice_corridas_que_no_vio(ajuste):
    aj, sol, *_ = ajuste
    sin_ruido = _filas(gen.VALIDACION_BANCO, 0.0, 0)
    pred = aj.predecir(sol.x, sin_ruido)
    real = np.array([[f["_medido"][k] for _, k in ab.PRODUCTOS] for f in sin_ruido])
    assert np.max(np.abs(pred - real) / 3.0) < 0.015  # menos de 1.5 % de la carga en cada producto


def test_avisa_si_el_balance_no_cierra(tmp_path, capsys):
    f = tmp_path / "b.csv"
    f.write_text("corrida,masa_kg,volumen_m3,T_C,P_bar,reflujo,T_defleg_C,T_cond_C,n2_mol_s,gasolina_kg,diesel_kg,"
                 "ceras_kg,gas_kg,coque_kg\nX,3,0.01,460,1.2,si,330,20,0.0005,0.5,1.0,0.1,0.3,0.05\n")
    ab.leer_corridas(f)
    assert "no cierra" in capsys.readouterr().out
