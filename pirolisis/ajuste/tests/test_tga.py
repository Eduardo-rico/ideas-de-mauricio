"""El ajuste de TGA debe recuperar parámetros conocidos de datos sintéticos."""
import numpy as np
import pytest

import cinetica_tga as ct
import generar_datos_prueba as gen


def _curvas(componentes, ruido=0.05):
    filas = gen.tga(componentes, ruido_pct=ruido)
    por_beta = {}
    for v, t, m in filas:
        por_beta.setdefault(v / 60, []).append((t + 273.15, m))
    return [ct.preparar(b, *np.array(sorted(p)).T) for b, p in sorted(por_beta.items())]


def test_friedman_y_kas_recuperan_ea_de_un_solo_plastico():
    curvas = _curvas([{"nombre": "PEAD", "A": 1.0e16, "Ea": 268e3, "fraccion": 1.0}])
    fr = [r["Ea_kJ_mol"] for r in ct.friedman(curvas) if 0.2 <= r["alpha"] <= 0.8]
    ka = [r["Ea_kJ_mol"] for r in ct.kas(curvas) if 0.2 <= r["alpha"] <= 0.8]
    assert np.median(fr) == pytest.approx(268, rel=0.02)
    assert np.median(ka) == pytest.approx(268, rel=0.03)


def test_ajuste_global_separa_la_mezcla_de_tres_plasticos():
    aj = ct.ajuste_global(_curvas(gen.VERDAD_TGA), n=3)
    assert aj["rmse_alpha"] < 0.003
    verdad = sorted(gen.VERDAD_TGA, key=lambda c: c["Ea"])  # PS, PP, PEAD; mismo orden que el ajuste
    for c, v in zip(aj["componentes"], verdad):
        assert c["Ea_kJ_mol"] == pytest.approx(v["Ea"] / 1000, rel=0.03)
        assert c["fraccion"] == pytest.approx(v["fraccion"], abs=0.02)
        assert c["log10A"] == pytest.approx(np.log10(v["A"]), abs=0.3)


def test_pide_tres_velocidades(tmp_path):
    f = tmp_path / "t.csv"
    f.write_text("velocidad_K_min,temperatura_C,masa\n10,200,100\n20,200,100\n")
    with pytest.raises(ValueError, match="al menos 3"):
        ct.leer_csv(f)
