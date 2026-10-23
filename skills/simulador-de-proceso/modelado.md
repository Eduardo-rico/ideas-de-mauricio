# Caja de herramientas de modelado

Todo en SI dentro del modelo (kg, K, Pa, mol, J, s); convierte sólo en la UI.

## Estructura del modelo

- **Especies o lumps** con las propiedades que el proceso use: `M` (kg/mol), `Tb` (K), `nv` (no volátil), densidad, viscosidad, número ácido, poder calorífico. Pocas especies bien elegidas > muchas sin datos.
- **Con reacciones:** M por estequiometría (p. ej. `M_TG = 3·M_FAME + M_GL − 3·M_MeOH`) y avance de reacción en moles.
- **Por etapa:** función pura `etapa(corriente, cfg) → { out, products, waste, E, time, info }`. Corriente = `{especie: kg}`.
- **Proceso dinámico** (reactor por lotes): `makeState(cfg)` + `step(s, cfg, dt)` con dt 0.2–0.5 s; la UI integra `velocidad × dtReal` en sub-pasos.
- Exporta con `if (typeof module !== 'undefined') module.exports = {...}` para las pruebas en node.

## Ecuaciones que ya funcionaron

| Fenómeno | Ecuación | Nota |
|---|---|---|
| Cinética | Arrhenius `k = A·exp(−Eₐ/RT)`, primer orden por especie | A en s⁻¹; revisa la unidad de la fuente (min⁻¹ ÷ 60) |
| Reacciones reversibles en serie (transesterificación, esterificación) | `r = k₁·C_A·C_B − k₋₁·C_C·C_D` por paso | Rígido: paso implícito o RK4 con dt chico; prueba que al reducir dt a la mitad el resultado no cambia y que a tiempo largo llega a K_eq |
| Separación líquido-líquido (decantar glicerina, extracción) | Coeficiente de reparto `K_D = C_fase1/C_fase2` por especie | `cal` si no hay dato; tiempo de decantación por Stokes |
| Presión de vapor, fracciones de petróleo | Maxwell–Bonnell (API TDB 5A1.19), T y Tb en °R | Usa la fórmula media para P ≥ 2 mmHg y la baja abajo; valida con octano 2.1 kPa a 27 °C |
| Presión de vapor, compuestos puros | Antoine (agua, 2-propanol…) | |
| Equilibrio líquido-vapor | Rachford–Rice con bisección; no condensables como `nc/N/V` | Escribe `(1−V)+V·K`, no `1+V(K−1)`: con K≈1e-15 pierde precisión |
| Evaporación continua (película, destilación por lotes) | Rayleigh: quita vapor `y_i = x_i·Psat_i/Pb` hasta `Pb = P_eff` | Los no volátiles disueltos diluyen; vapor de arrastre fijo: `P_eff = P·n0/(n0+nc)` |
| Termodinámica rigurosa | Peng–Robinson + pseudocomponentes Riazi–Daubert / Lee–Kesler | En Python (`pirolisis/termo/`) para revisar las reglas simples |
| Presión del recipiente | Gas ideal + válvula `ṅ = Kv·max(0, P−Pset)` implícita | PSV como segunda válvula |
| Energía | Dos nodos (pared/contenido) con intercambio implícito 2×2; fusión como cp aparente gaussiano | Pérdidas desde la pared; UA ∝ V^(2/3) |
| Calor pared → fundido | Ancla de Uhl y Gray `Nu = 0.36 Re^(2/3) Pr^(1/3)`, h mínimo | La viscosidad baja con la conversión |
| Sedimentación | Stokes sobre distribución lognormal, `min(1, v·t/H)` | Viscosidad de Walther (ASTM D341) |
| Adsorción | Freundlich `C0 = C + (m_ads/m)·K·C^(1/n)`, bisección | |
| Viscosidad de mezcla | Refutas (VBN) | |
| Seguridad del recipiente | ASME VIII UG-27/UG-32, API 520/521, orificios API 526 | `pirolisis/mecanica/hoja.py` |

## Pruebas mínimas en `escenarios.test.js`

1. **Propiedades contra un dato medido** (una presión de vapor, un punto de ebullición).
2. **Balance de masa** con error relativo < 1e-9 en todas las rutas y en condiciones extremas (sin reactivo, máximo, mínimo); con reacciones, también por moles o átomos.
3. **Sin NaN ni masas negativas** en ninguna corriente.
4. **Tendencias de la literatura:** más temperatura → más rápido; más presión → más craqueo; más adsorbente → mejor color, etc.
5. **Rendimiento dentro del rango reportado.**
6. Si hay una versión en Python, **Python ≡ JS** al 1e-9.

Escribe `✓` o `✗` por prueba y termina con `process.exit(fallas ? 1 : 0)`.

## Calibrar sin hacer trampa

- Primero que el modelo sea físico (Rayleigh, dilución, límite de pared); luego ajusta constantes.
- Ajusta para reproducir un número publicado y dilo en la tabla de parámetros.
- Si un cambio de parámetro produce un salto brusco (rendimiento 65 → 46 %), busca el error de formulación antes de suavizarlo.
