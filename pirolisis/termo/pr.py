"""Ecuación de estado de Peng–Robinson: fugacidades, entalpía residual, flash PT y punto de burbuja.

Peng y Robinson (1976), con κ de la versión de 1978 para ω > 0.49 (pseudocomponentes pesados).
Reglas de mezcla de van der Waals con k_ij = 0 salvo N2/H2–hidrocarburo (valores típicos de DWSIM/HYSYS).
Unidades SI: T en K, P en Pa, cantidades en mol.
"""
import math

import numpy as np
from scipy.optimize import brentq

R = 8.314462618
S2 = math.sqrt(2.0)


class PR:
    def __init__(self, comps, kij=None):
        self.c = list(comps)
        self.n = len(self.c)
        self.Tc = np.array([c.Tc for c in self.c])
        self.Pc = np.array([c.Pc for c in self.c])
        self.w = np.array([c.w for c in self.c])
        self.M = np.array([c.M for c in self.c])
        self.kap = np.where(self.w <= 0.49, 0.37464 + 1.54226 * self.w - 0.26992 * self.w ** 2,
                            0.379642 + 1.48503 * self.w - 0.164423 * self.w ** 2 + 0.016666 * self.w ** 3)
        self.ac = 0.45724 * R ** 2 * self.Tc ** 2 / self.Pc
        self.b = 0.07780 * R * self.Tc / self.Pc
        self.k = np.zeros((self.n, self.n)) if kij is None else np.asarray(kij)
        if kij is None:
            ligeros = [i for i, c in enumerate(self.c) if c.nombre in ("Nitrógeno", "Hidrógeno")]
            for i in ligeros:
                for j in range(self.n):
                    if j not in ligeros:
                        self.k[i, j] = self.k[j, i] = 0.08

    def _a(self, T):
        sq = 1 + self.kap * (1 - np.sqrt(T / self.Tc))
        ai = self.ac * sq ** 2
        dai = -self.ac * self.kap * sq / np.sqrt(T * self.Tc)
        aij = (1 - self.k) * np.sqrt(np.outer(ai, ai))
        return ai, dai, aij

    def _Z(self, A, B, fase):
        r = np.roots([1.0, -(1 - B), A - 3 * B * B - 2 * B, -(A * B - B * B - B ** 3)])
        z = np.sort(r[np.abs(r.imag) < 1e-9].real)
        z = z[z > B]
        if len(z) == 0:
            raise ArithmeticError("Peng–Robinson sin raíz física")
        if fase == "L":
            return z[0]
        if fase == "V":
            return z[-1]
        if len(z) == 1:
            return z[0]
        g = [self._g(zz, A, B) for zz in (z[0], z[-1])]
        return z[0] if g[0] < g[1] else z[-1]

    @staticmethod
    def _g(Z, A, B):
        return Z - 1 - math.log(Z - B) - A / (2 * S2 * B) * math.log((Z + (1 + S2) * B) / (Z + (1 - S2) * B))

    def _mezcla(self, x, T, P):
        ai, dai, aij = self._a(T)
        a = x @ aij @ x
        b = x @ self.b
        return ai, dai, aij, a, b, a * P / (R * T) ** 2, b * P / (R * T)

    def lnphi(self, x, T, P, fase):
        x = np.asarray(x, float) / np.sum(x)
        _, _, aij, a, b, A, B = self._mezcla(x, T, P)
        Z = self._Z(A, B, fase)
        L = math.log((Z + (1 + S2) * B) / (Z + (1 - S2) * B))
        return (self.b / b * (Z - 1) - math.log(Z - B) - A / (2 * S2 * B) * (2 * (aij @ x) / a - self.b / b) * L), Z

    def h_residual(self, x, T, P, fase):
        """H − H_gas ideal, J/mol."""
        x = np.asarray(x, float) / np.sum(x)
        ai, dai, aij, a, b, A, B = self._mezcla(x, T, P)
        Z = self._Z(A, B, fase)
        daij = (1 - self.k) * 0.5 * (np.outer(dai, ai) + np.outer(ai, dai)) / np.sqrt(np.outer(ai, ai))
        dadT = x @ daij @ x
        L = math.log((Z + (1 + S2) * B) / (Z + (1 - S2) * B))
        return R * T * (Z - 1) + (T * dadT - a) / (2 * S2 * b) * L

    def wilson(self, T, P):
        return self.Pc / P * np.exp(5.373 * (1 + self.w) * (1 - self.Tc / T))

    def flash(self, z, T, P, tol=1e-11, iters=500):
        """Flash isotérmico. Regresa (V, x, y): fracción molar de vapor y composiciones."""
        z = np.asarray(z, float) / np.sum(z)
        K = self.wilson(T, P)
        V = 0.5
        for _ in range(iters):
            K = np.clip(K, 1e-300, 1e300)
            # (1 − v) + v·K en vez de 1 + v(K − 1): no pierde precisión cuando K ≈ 0
            f = lambda v: np.sum(z * (K - 1) / ((1 - v) + v * K))
            if f(0.0) <= 0:
                V = 0.0
            elif f(1.0) >= 0:
                V = 1.0
            else:
                # f(0) > 0 > f(1) y f es monótona en [0, 1]: la raíz está ahí aunque K_min ≈ 1e-15
                V = brentq(f, 0.0, 1.0, xtol=1e-15)
            x = z / ((1 - V) + V * K)
            y = K * x
            x, y = x / x.sum(), y / y.sum()
            lpl, _ = self.lnphi(x, T, P, "L")
            lpv, _ = self.lnphi(y, T, P, "V")
            Kn = np.exp(lpl - lpv)
            err = np.max(np.abs(np.log(Kn) - np.log(K)))
            K = Kn
            if err < tol:
                break
        if V in (0.0, 1.0):
            return V, z.copy(), z.copy()
        return V, x, y

    def p_burbuja(self, x, T, P0=1e5, iters=200):
        """Presión de burbuja de un líquido x a T (presión de vapor verdadera de la mezcla)."""
        x = np.asarray(x, float) / np.sum(x)
        P = P0
        y = x * self.wilson(T, P)
        y /= y.sum()
        for _ in range(iters):
            lpl, _ = self.lnphi(x, T, P, "L")
            lpv, _ = self.lnphi(y, T, P, "V")
            Ky = x * np.exp(lpl - lpv)
            s = Ky.sum()
            y = Ky / s
            Pn = P * s
            if abs(Pn - P) / P < 1e-10:
                return Pn
            P = Pn
        return P


def cp_gas_ideal(T):
    """Cp de gas ideal de hidrocarburos, J/(kg·K). Aproximación lineal para C1–C40 (±10 % entre 300 y 800 K)."""
    return 600.0 + 3.4 * T


def h_ideal_masa(T, T0=298.15):
    """∫ Cp dT desde T0, J/kg."""
    return 600.0 * (T - T0) + 1.7 * (T * T - T0 * T0)
