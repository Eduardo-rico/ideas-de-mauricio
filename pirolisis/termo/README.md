# Termodinámica del tren de separación

Peng–Robinson con pseudocomponentes para lo que pasa después del reactor: deflegmador, condensador y corte del aceite en gasolina, diésel y ceras. Sirve para dos cosas:

1. **Dimensionar:** calor que retira cada equipo, agua de enfriamiento, cuánta gasolina se escapa con el gas y la presión de vapor de la gasolina.
2. **Revisar el simulador web**, que usa reglas simples (Clausius–Clapeyron + Trouton), y ver cuánto se equivocan.

```bash
cd pirolisis/termo
uv sync
uv run python diagrama.py                         # caso base: 460 °C, 1.2 bar, deflegmador a 280 °C
uv run python diagrama.py --Td 300 --P 2.5 --Tc 15
uv run python diagrama.py --dwsim receta_dwsim.md # receta para armarlo en DWSIM
uv run pytest                                     # 19 pruebas
```

## Qué encontró (caso base, 15 kg/h de vapor)

| | Peng–Robinson | Simulador web |
|---|---|---|
| Ceras que regresa el deflegmador a 330 °C | 22 % | antes 87 %; ahora 24 % (corregido) |
| Ceras que regresa a 280 °C | 81 % | 82 % |
| Gasolina que se escapa con el gas a 30 °C | 11 % | 6 % (subestima: los C5–C6 son muy volátiles) |
| Gas C1–C4 disuelto en el aceite | 1.4 % | no lo modela |
| Presión de vapor de la gasolina a 37.8 °C | 247 kPa con gas disuelto, 19 kPa estabilizada | no lo modela |

Consecuencias:
- **La regla vieja del deflegmador no tomaba en cuenta que las ceras van diluidas en gas y N₂.** Ahora el simulador hace un flash ideal con Rachford–Rice, que da casi lo mismo que Peng–Robinson. El reflujo útil queda entre 260 y 280 °C, no a 330 °C.
- **La gasolina sale con propano y butano disueltos.** Para venderla hace falta una columna estabilizadora (debutanizadora) que los quite antes de medir su presión de vapor contra la NOM-016-CRE-2016.
- **Agua de enfriamiento:** el condensador necesita unos 3.7 L/min de agua de 20 a 30 °C por cada 15 kg/h de vapor.

## Cómo está hecho

- `componentes.py` — 9 gases puros (Poling et al., 5.ª ed.) y 11 pseudocomponentes por grupo de carbonos (C5–C6 … C33–C40). Tc, Pc y M salen de Riazi–Daubert (1987) y ω de Lee–Kesler, con SG del factor de Watson K = 12.5 (aceite parafínico-olefínico). `pseudos_de_destilacion()` genera pseudocomponentes a partir de tu destilación simulada ASTM D2887.
- `pr.py` — Peng–Robinson (κ de 1978 para ω > 0.49), fugacidades, entalpía residual, flash PT con Rachford–Rice y sustitución sucesiva, y presión de burbuja. k_ij = 0.08 entre N₂/H₂ e hidrocarburos.
- `diagrama.py` — el tren completo y la comparación con el simulador.
- Las pruebas comparan contra datos medidos: presión de vapor del hexano y del propano, calor de vaporización del hexano, propiedades críticas del octano y peso molecular del triacontano. También revisan que la masa cierre en el tren.

## Limitaciones

- **Cp de gas ideal lineal** (±10 % entre 300 y 800 K). Afecta los calores de los equipos, no los equilibrios.
- **El deflegmador es una sola etapa de equilibrio.** Una columna empacada con 2–3 etapas teóricas regresa más cera y menos diésel. Para eso, arma la columna rigurosa en DWSIM con `receta_dwsim.md`.
- **Composición inventada:** la del gas es típica de poliolefinas y la del aceite se reparte por igual dentro de cada lump. Reemplázalas con tu cromatografía y tu destilación simulada.
