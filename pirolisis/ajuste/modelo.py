"""Modelo de lumps de pirólisis semi-batch: traducción fiel de ../model.js.

Unidades SI (kg, K, Pa, mol, J, s). La única diferencia con la versión de la
página es que los parámetros viven en un diccionario `p` para poder ajustarlos.
tests/test_modelo.py comprueba que ambos dan el mismo resultado.
"""
import copy
import math

R, PATM = 8.314, 101325.0

DEFAULTS = {
    "RHO": 750.0, "CP_POLY": 2400.0, "CP_LIQ": 2500.0, "CP_CHAR": 1000.0, "CP_STEEL": 500.0,
    "K_EV": 0.15, "KV": 2e-5, "KR": 1e-3, "P_RELIEF": 6e5, "DH_SEC": 0.3e6,
    "LHV_GAS": 46e6, "ETA_B": 0.75, "KP": 2500.0, "KI": 8.0,
    "POLY": {
        "HDPE": {"A": 1.0e16, "Ea": 268e3, "s": {"W": .55, "D": .22, "G": .13, "Gs": .08, "C": .02}, "Tm": 403, "dHm": 190e3, "dHr": 1.05e6},
        "LDPE": {"A": 2.2e14, "Ea": 240e3, "s": {"W": .45, "D": .27, "G": .16, "Gs": .10, "C": .02}, "Tm": 383, "dHm": 120e3, "dHr": 0.95e6},
        "PP":   {"A": 1.9e13, "Ea": 220e3, "s": {"W": .30, "D": .32, "G": .25, "Gs": .11, "C": .02}, "Tm": 438, "dHm": 90e3,  "dHr": 0.85e6},
        "PS":   {"A": 3.0e12, "Ea": 200e3, "s": {"W": .10, "D": .15, "G": .65, "Gs": .03, "C": .07}, "Tm": 0,   "dHm": 0.0,   "dHr": 0.65e6},
    },
    "LUMP": {"W": {"M": 0.45, "Tb": 780}, "D": {"M": 0.23, "Tb": 560}, "G": {"M": 0.10, "Tb": 400}, "Gs": {"M": 0.03}},
    "SEC": {
        "W": {"A": 2e11,   "Ea": 180e3, "to": {"D": .75, "G": .20, "Gs": .05}},
        "D": {"A": 1e12,   "Ea": 200e3, "to": {"G": .80, "Gs": .20}},
        "G": {"A": 1.2e12, "Ea": 210e3, "to": {"Gs": 1.0}},
    },
    "COKE": {"A": 1e8, "Ea": 170e3},
    "CAT": {
        "none": {"beta": 0, "smax": 0,   "to": None},
        "FCC":  {"beta": 2, "smax": .60, "to": {"D": .45, "G": .45, "Gs": .07, "C": .03}},
        "HY":   {"beta": 3, "smax": .75, "to": {"D": .30, "G": .55, "Gs": .10, "C": .05}},
        "ZSM5": {"beta": 4, "smax": .85, "to": {"G": .70, "Gs": .25, "C": .05}},
    },
}

LIQ = ("W", "D", "G")
ALL = ("W", "D", "G", "Gs")


def parametros(**cambios):
    """Copia de los parámetros por defecto con cambios de primer nivel."""
    p = copy.deepcopy(DEFAULTS)
    p.update(copy.deepcopy(cambios))
    return p


def dhv(p, i):
    return 88 * p["LUMP"][i]["Tb"] / p["LUMP"][i]["M"]


def psat(Tb, T):
    return PATM * math.exp(min(40.0, (88 / R) * (1 - Tb / T)))


def clamp(x, a, b):
    return a if x < a else b if x > b else x


def config(**kw):
    """Condiciones de operación con los mismos valores por defecto que la página."""
    c = {"mix": {"HDPE": 40, "LDPE": 20, "PP": 30, "PS": 10}, "mass": 50.0, "Vr": 0.3,
         "Tamb": 298.0, "Tsp": 733.15, "Pmax": 40000.0, "Pset": 1.2e5, "reflux": True,
         "Tref": 603.15, "Tc": 298.15, "n2": 0.005, "cat": "none", "catLoad": 0.0, "recirc": True}
    c.update(kw)
    # acero y pérdidas escalan con el área del recipiente (∝ V^2/3); a 0.3 m3: 150 kg y 29 W/K
    c.setdefault("mSteel", 335 * c["Vr"] ** (2 / 3))
    c.setdefault("UA", 64 * c["Vr"] ** (2 / 3))
    return c


def reflux_flash(out, nN2, Td, P, LUMP):
    """Fracción de cada lump que condensa en un flash ideal a (Td, P); Gs y N2 no condensan."""
    n = {i: out[i] / LUMP[i]["M"] for i in LIQ}
    K = {i: psat(LUMP[i]["Tb"], Td) / P for i in LIQ}
    nNC = nN2 + out["Gs"] / LUMP["Gs"]["M"]
    N = nNC + sum(n.values())
    if N <= 0:
        return {i: 0.0 for i in LIQ}

    def f(V):
        return nNC / N / V + sum(n[i] / N * (K[i] - 1) / ((1 - V) + V * K[i]) for i in LIQ)

    if f(1.0) >= 0:
        return {i: 0.0 for i in LIQ}
    lo, hi = 1e-9, 1.0
    if f(lo) <= 0:
        return {i: 1.0 for i in LIQ}
    for _ in range(60):
        m = 0.5 * (lo + hi)
        if f(m) > 0:
            lo = m
        else:
            hi = m
    V = 0.5 * (lo + hi)
    return {i: (1 - V) / ((1 - V) + V * K[i]) for i in LIQ}


def make_state(c, p):
    tot = sum(c["mix"].values())
    mP = {k: (c["mass"] * v / tot if tot > 0 else 0.0) for k, v in c["mix"].items()}
    Vh = max(0.01, c["Vr"] - c["mass"] / p["RHO"])
    return {
        "t": 0.0, "T": c["Tamb"], "P": PATM, "I": 0.0, "Q": 0.0, "Qgas": 0.0, "relief": False,
        "done": False, "tau": math.inf, "mP": mP, "mass0": c["mass"],
        "L": {"W": 0.0, "D": 0.0, "G": 0.0}, "V": {"W": 0.0, "D": 0.0, "G": 0.0, "Gs": 0.0},
        "nN2": PATM * Vh / (R * c["Tamb"]), "char": 0.0, "tank": {"G": 0.0, "D": 0.0, "W": 0.0},
        "gasFlare": 0.0, "gasBurn": 0.0, "gasLossG": 0.0, "Eext": 0.0, "Egas": 0.0, "tDone": 0.0,
        "Qloss": 0.0, "Qrxn": 0.0,
    }


def step(s, c, p, dt):
    T = s["T"]
    RT = R * T
    L, V, LUMP = s["L"], s["V"], p["LUMP"]
    mPtot = sum(s["mP"].values())
    Ltot = L["W"] + L["D"] + L["G"]
    Vh = max(0.01, c["Vr"] - (mPtot + Ltot + s["char"]) / p["RHO"])
    cat, phi = p["CAT"][c["cat"]], c["catLoad"]
    mult = 1 + cat["beta"] * phi / 0.1
    sig = cat["smax"] * phi / (phi + 0.05)

    # 1. Craqueo primario
    Qr = 0.0
    for j, m in s["mP"].items():
        if m <= 0:
            continue
        pj = p["POLY"][j]
        r = min(pj["A"] * math.exp(-pj["Ea"] / RT) * mult * m, m / dt)
        s["mP"][j] = m - r * dt
        x, sj = r * dt, pj["s"]
        sh = sig * sj["W"]
        L["W"] += x * (sj["W"] - sh); L["D"] += x * sj["D"]; L["G"] += x * sj["G"]
        V["Gs"] += x * sj["Gs"]; s["char"] += x * sj["C"]
        if cat["to"]:
            y, to = x * sh, cat["to"]
            L["D"] += y * to.get("D", 0); L["G"] += y * to.get("G", 0)
            V["Gs"] += y * to.get("Gs", 0); s["char"] += y * to.get("C", 0)
        Qr += r * pj["dHr"]

    # 2. Craqueo secundario
    Qs = 0.0
    for i in LIQ:
        q = p["SEC"][i]
        k = q["A"] * math.exp(-q["Ea"] / RT) * mult
        rl = min(k * L[i], L[i] / dt)
        rv = min(0.5 * k * V[i], V[i] / dt)
        L[i] -= rl * dt; V[i] -= rv * dt
        for o, f in q["to"].items():
            if o == "Gs":
                V["Gs"] += (rl + rv) * f * dt
            else:
                L[o] += rl * f * dt; V[o] += rv * f * dt
        Qs += (rl + rv) * p["DH_SEC"]
    kc = p["COKE"]["A"] * math.exp(-p["COKE"]["Ea"] / RT)
    for i in ("W", "D"):
        r = min(kc * L[i], L[i] / dt)
        L[i] -= r * dt; s["char"] += r * dt

    # 3. Evaporación
    Qv = 0.0
    for i in LIQ:
        f = min(1.0, psat(LUMP[i]["Tb"], T) / s["P"])
        e = min(p["K_EV"] * f * L[i], L[i] / dt)
        L[i] -= e * dt; V[i] += e * dt
        Qv += e * dhv(p, i)

    # 4. Purga de N2
    s["nN2"] += c["n2"] * dt

    # 5. Presión y válvulas (implícito)
    N0 = s["nN2"] + sum(V[i] / LUMP[i]["M"] for i in ALL)
    cc = RT / Vh
    N1 = N0
    KV, KR, PR = p["KV"], p["KR"], p["P_RELIEF"]
    if cc * N0 > c["Pset"]:
        N1 = (N0 + dt * KV * c["Pset"]) / (1 + dt * KV * cc)
        if cc * N1 > PR:
            N1 = (N0 + dt * (KV * c["Pset"] + KR * PR)) / (1 + dt * (KV + KR) * cc)
    s["relief"] = cc * N1 > PR * 0.98
    frac = (N0 - N1) / N0 if N0 > 0 else 0.0
    out = {}
    for i in ALL:
        out[i] = V[i] * frac
        V[i] -= out[i]
    outN2 = s["nN2"] * frac
    s["nN2"] -= outN2
    s["P"] = cc * N1
    nOut = (N0 - N1) / dt
    s["tau"] = N1 / nOut if nOut > 1e-6 else math.inf

    # 6. Deflegmador: una etapa de equilibrio a Td (Raoult + Rachford–Rice)
    if c["reflux"]:
        liq = reflux_flash(out, outN2, min(c["Tref"], T), s["P"], LUMP)
        for i in LIQ:
            b = out[i] * liq[i]
            out[i] -= b; L[i] += b

    # 7. Condensador
    PsG = psat(LUMP["G"]["Tb"], c["Tc"])
    lossG = 0.0
    if PsG < s["P"]:
        nNC = outN2 + out["Gs"] / LUMP["Gs"]["M"]
        lossG = min(out["G"], nNC * PsG / (s["P"] - PsG) * LUMP["G"]["M"])
    s["tank"]["W"] += out["W"]; s["tank"]["D"] += out["D"]; s["tank"]["G"] += out["G"] - lossG
    s["gasLossG"] += lossG
    gasM = out["Gs"] + lossG

    # 8. Calentador PI y gas recirculado
    e = c["Tsp"] - T
    if abs(e) < 25:
        s["I"] = clamp(s["I"] + p["KI"] * e * dt, 0, c["Pmax"])
    Q = clamp(p["KP"] * e + s["I"], 0, c["Pmax"])
    Qgas = burn = 0.0
    if c["recirc"] and gasM > 0:
        Qgas = min(Q, gasM / dt * p["LHV_GAS"] * p["ETA_B"])
        burn = Qgas * dt / (p["LHV_GAS"] * p["ETA_B"])
    s["gasBurn"] += burn; s["gasFlare"] += gasM - burn
    s["Eext"] += (Q - Qgas) * dt; s["Egas"] += Qgas * dt
    s["Q"], s["Qgas"] = Q, Qgas

    # 9. Balance de energía
    C = c["mSteel"] * p["CP_STEEL"] + Ltot * p["CP_LIQ"] + s["char"] * p["CP_CHAR"]
    for j, m in s["mP"].items():
        pj = p["POLY"][j]
        C += m * p["CP_POLY"]
        if pj["dHm"] > 0:
            z = (T - pj["Tm"]) / 6
            C += m * pj["dHm"] * math.exp(-0.5 * z * z) / (6 * 2.5066)
    s["Qloss"] = c["UA"] * (T - c["Tamb"])
    s["Qrxn"] = Qr + Qs + Qv
    s["T"] = T + (Q - Qr - Qs - Qv - s["Qloss"]) / C * dt
    s["t"] += dt

    if not s["done"] and s["t"] > 600 and mPtot + Ltot < 0.003 * s["mass0"]:
        s["done"] = True
        s["tDone"] = s["t"]


def resumen(s):
    mP = sum(s["mP"].values())
    Lt = sum(s["L"].values())
    Vt = sum(s["V"].values())
    gas = s["gasFlare"] + s["gasBurn"]
    acc = s["tank"]["G"] + s["tank"]["D"] + s["tank"]["W"] + gas + s["char"] + mP + Lt + Vt
    return {"G": s["tank"]["G"], "D": s["tank"]["D"], "W": s["tank"]["W"], "gas": gas,
            "char": s["char"], "inside": mP + Lt + Vt, "conv": 1 - mP / s["mass0"],
            "closure": acc / s["mass0"] - 1, "t": s["t"]}


def simular(c, p=None, dt=0.2, t_max=8 * 3600):
    """Corre un lote completo y regresa el resumen (kg de cada producto)."""
    p = p or DEFAULTS
    s = make_state(c, p)
    while s["t"] < t_max and not s["done"]:
        step(s, c, p, dt)
    return resumen(s)
