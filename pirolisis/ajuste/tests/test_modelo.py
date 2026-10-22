"""La traducción a Python debe dar lo mismo que el modelo de la página (model.js)."""
import json
import pathlib
import shutil
import subprocess

import pytest

import modelo

MODEL_JS = pathlib.Path(__file__).resolve().parents[2] / "model.js"

CASOS = [
    {},
    {"reflux": False, "Pset": 1.05e5},
    {"mix": {"PP": 1}, "Tsp": 743.15, "cat": "ZSM5", "catLoad": 0.1, "Pset": 2.5e5, "Tref": 513.15},
]


@pytest.mark.skipif(shutil.which("node") is None, reason="se necesita node para correr model.js")
@pytest.mark.parametrize("cambios", CASOS)
def test_igual_que_model_js(cambios):
    c = modelo.config(**cambios)
    py = modelo.simular(c, dt=0.5)
    js_code = f"""
const M = require({json.dumps(str(MODEL_JS))});
const c = {json.dumps(c)};
const s = M.makeState(c);
while (s.t < 8*3600 && !s.done) M.step(s, c, 0.5);
console.log(JSON.stringify(M.summary(s)));
"""
    js = json.loads(subprocess.run(["node", "-e", js_code], capture_output=True, text=True, check=True).stdout)
    for k in ("G", "D", "W", "gas", "char", "inside"):
        assert py[k] == pytest.approx(js[k], rel=1e-9, abs=1e-9), k


def test_balance_de_masa_cierra():
    r = modelo.simular(modelo.config(), dt=0.5)
    assert abs(r["closure"]) < 1e-10
    assert r["conv"] > 0.99
