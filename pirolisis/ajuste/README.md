# Ajuste cinético con datos propios

Convierte mediciones de laboratorio en los parámetros del simulador de pirólisis, para que deje de usar valores de la literatura y use los de **tu** plástico.

| Etapa | Qué mides | Qué sale | Script |
|---|---|---|---|
| 1. TGA | Pérdida de masa contra temperatura a 3–4 velocidades | A y Eₐ de cada plástico de la mezcla y su fracción | `cinetica_tga.py` |
| 2. Reactor de banco | kg de gasolina, diésel, ceras, gas y coque por corrida | Selectividades y craqueo secundario, con incertidumbre | `ajuste_banco.py` |

## Instalación

```bash
cd pirolisis/ajuste
uv sync          # instala numpy, scipy, matplotlib y pytest en .venv
```

## Prueba rápida con datos sintéticos

```bash
uv run python generar_datos_prueba.py ejemplo
uv run python cinetica_tga.py ejemplo/tga_sintetico.csv --componentes 3 --salida resultados
uv run python ajuste_banco.py ejemplo/banco_sintetico.csv --tga resultados/cinetica_tga.json \
       --validar ejemplo/banco_validacion.csv --salida resultados
uv run pytest    # 12 pruebas: el modelo en Python = model.js, y los ajustes recuperan los parámetros verdaderos
```

Con los datos sintéticos, la TGA recupera Eₐ = 199 / 220 / 268 kJ/mol (las verdaderas son 200 / 220 / 268) y las fracciones de la mezcla exactas. El banco recupera las selectividades a ±0.01 y el craqueo de ceras a ±30 %. Las constantes de diésel y gasolina salen con ±60–80 %: con 6 corridas no se separan mejor, y el script lo dice.

## Protocolo de TGA

Sigue las recomendaciones del comité de cinética de la ICTAC (Vyazovkin et al., *Thermochimica Acta* 520, 2011).

1. **Muestra representativa:** muele la mezcla (de preferencia con nitrógeno líquido) a menos de 0.5 mm y homogeneiza. Seca 2 h a 105 °C.
2. **5–10 mg** en crisol de alúmina, **N₂ a 50–100 mL/min**, purga 30 min antes de calentar.
3. **Rampas de 5, 10, 20 y 40 °C/min** (mínimo 3) de 30 a 650 °C. Repite una por duplicado para conocer tu error.
4. Haz una corrida en blanco para corregir la flotación y usa la **temperatura de la muestra**, no la del horno.
5. Exporta un solo CSV con las columnas `velocidad_K_min, temperatura_C, masa` (mg o %).

Cómo leer el resultado:
- Si **Eₐ de Friedman cambia más de 20 %** con la conversión, hay varias reacciones. Usa `--componentes` igual al número de picos del DTG (normalmente uno por plástico).
- Si **RMSE en α > 0.02**, agrega un componente o usa `--orden-libre`.
- **Friedman y KAS deben coincidir más o menos**; si no, revisa la temperatura y la línea base.

## Protocolo del reactor de banco (2–5 kg)

Diseño mínimo de 6 corridas para que cada parámetro tenga algo que lo mueva:

| Corrida | T | Presión | Deflegmador | Para qué |
|---|---|---|---|---|
| B1–B3 | 440 / 460 / 480 °C | 1.2 bar | 330 °C | Efecto de temperatura |
| B4 | 460 °C | 1.2 bar | apagado | Separa craqueo de ceras |
| B5 | 460 °C | 2.5 bar | 330 °C | Tiempo de residencia del vapor |
| B6 | 460 °C | 1.2 bar | 270 °C | Separa craqueo de diésel |

Más 1–2 corridas en otras condiciones para `--validar`, y una repetida para conocer el error experimental.

- **Pesa todo:** la carga, cada tanque y el coque. El gas puede ir por diferencia. Si los productos no suman 95–105 % de la carga, el script avisa.
- **Separa gasolina y diésel por destilación:** corte a 180 °C (ASTM D86), o reporta con destilación simulada (ASTM D2887). Lo que hierve arriba de 360 °C son ceras.
- **Con `--ajustar-ea`** (corridas a ≥ 3 temperaturas) también se ajustan las Eₐ secundarias.

Formato del CSV: ver `ejemplo/banco_sintetico.csv`. Opcionales: `potencia_kW`, `UA_W_K` (pérdidas del reactor, W/K) y `masa_acero_kg`.

## Archivos

- `modelo.py` — el modelo de la página traducido a Python, con los parámetros en un diccionario. `tests/test_modelo.py` comprueba que da exactamente lo mismo que `../model.js`.
- `cinetica_tga.py` — Friedman, KAS y ajuste global de N reacciones paralelas. Salida: `cinetica_tga.json` y una gráfica.
- `ajuste_banco.py` — mínimos cuadrados con matriz de covarianza; avisa cuando dos parámetros no se pueden separar. Salida: `ajuste_banco.json` con `POLY` y `SEC` listos para el simulador.
- `generar_datos_prueba.py` — datos sintéticos con parámetros conocidos.
