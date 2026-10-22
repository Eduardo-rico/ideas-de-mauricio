# Ideas de Mauricio

## Pirólisis a Combustibles (`pirolisis/`)

Planta piloto virtual que convierte plástico (PEAD, PEBD, PP, PS) en gasolina, diésel, ceras, gas y coque en un reactor por lotes. Simula en tiempo real balance de masa, presión (gas ideal + válvula de contrapresión y PSV) y energía, con diagrama animado, gráficas y la lista de equipo para armar la planta.

- `pirolisis/index.html` — la página completa; ábrela en el navegador, no necesita servidor.
- `pirolisis/model.js` — el modelo matemático solo (el mismo que trae la página).
- `pirolisis/escenarios.test.js` — corre escenarios de prueba: `cd pirolisis && node escenarios.test.js`.

El modelo es de lumps y semicuantitativo: sirve para aprender y comparar condiciones, no para dimensionar equipo. La cinética del PEAD y PP viene de Bockhorn (1999); las selectividades y el craqueo secundario están calibrados a tendencias de la literatura. Las fuentes están al final de la página.
