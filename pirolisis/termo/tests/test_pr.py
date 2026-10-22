"""Peng–Robinson y las correlaciones de pseudocomponentes contra valores conocidos."""
import numpy as np
import pytest

import componentes as cm
from pr import PR


def test_presion_de_vapor_del_hexano_en_su_ebullicion_normal():
    pr = PR([cm.PUROS["nC6"]])
    assert pr.p_burbuja([1.0], 341.88) == pytest.approx(101325, rel=0.03)


def test_presion_de_vapor_del_propano_a_25C():
    pr = PR([cm.PUROS["C3H8"]])
    assert pr.p_burbuja([1.0], 298.15) == pytest.approx(9.52e5, rel=0.03)  # 9.5 bar, tablas NIST


def test_riazi_daubert_reproduce_al_octano():
    M, Tc, Pc = cm.riazi_daubert(398.8, 0.703)
    assert M == pytest.approx(114.2, rel=0.12)
    assert Tc == pytest.approx(568.7, rel=0.02)
    assert Pc == pytest.approx(24.9, rel=0.06)
    assert cm.acentrico(398.8, Tc, Pc, 0.703) == pytest.approx(0.399, abs=0.05)


def test_riazi_daubert_reproduce_al_triacontano():
    M, Tc, Pc = cm.riazi_daubert(722.9, 0.874)
    assert M == pytest.approx(422.8, rel=0.05)


def test_el_pseudocomponente_hierve_a_su_tb():
    p = cm.pseudo("C15-C16", 551.9)
    assert PR([p]).p_burbuja([1.0], 551.9) == pytest.approx(101325, rel=0.10)


def test_flash_conserva_la_masa_y_separa_ligeros_de_pesados():
    comps = [cm.PUROS["CH4"], cm.PUROS["C3H8"], cm.pseudo("C9-C10", 435.6), cm.pseudo("C19-C22", 622.9)]
    pr = PR(comps)
    z = np.array([0.3, 0.2, 0.3, 0.2])
    V, x, y = pr.flash(z, 320.0, 1.2e5)
    assert 0 < V < 1
    assert np.allclose(V * y + (1 - V) * x, z, atol=1e-10)
    assert y[0] > z[0] > x[0] and x[3] > z[3] > y[3]


def test_flash_todo_vapor_y_todo_liquido():
    pr = PR([cm.PUROS["CH4"], cm.pseudo("C9-C10", 435.6)])
    assert pr.flash([0.5, 0.5], 700.0, 1e5)[0] == 1.0
    assert pr.flash([0.001, 0.999], 300.0, 20e5)[0] == 0.0


def test_entalpia_de_vaporizacion_del_hexano():
    pr = PR([cm.PUROS["nC6"]])
    T = 341.88
    hv = pr.h_residual([1.0], T, 101325, "V") - pr.h_residual([1.0], T, 101325, "L")
    assert hv == pytest.approx(28.85e3, rel=0.06)  # 28.85 kJ/mol medido
