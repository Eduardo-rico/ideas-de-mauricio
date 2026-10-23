# Búnker Celaya

Simulación hora por hora de un búnker enterrado en Celaya, Gto., para 5 personas y 4 perros durante 3 años: desde la detonación y la lluvia radiactiva hasta el invierno nuclear.

Cada componente tiene su propio modelo:
- **Blindaje:** espesores de medio valor y límite por la entrada; regla t^−1.2.
- **Ventilación filtrada y depurador de CO₂:** cal sodada.
- **Cultivos bajo LED:** hidroponía y aeroponía, con la eficiencia de luz de NASA.
- **Algas y pecera de tilapia.**
- **Energía:** paneles con el sol reducido por el hollín, baterías y generador, con prioridades de carga.
- **Agua:** cisternas, lluvia, deshumidificador y aguas grises.
- **Comida guardada y temperatura.**

- `index.html` — la página: corte animado del búnker, línea de tiempo de 3 años, gráficas, qué se acaba y cuándo, ecuaciones y presupuesto con precios.
- `model.js` — el modelo.
- `escenarios.test.js` — 26 pruebas: `node escenarios.test.js`.
  - Los balances de energía, batería, agua, O₂ y CO₂ cierran en 7 casos.
  - El O₂ y el CO₂ por persona coinciden con NASA BVAD.
  - La regla 7:10 se cumple, y también las tendencias.

Lo que muestra con el diseño base:
- **Aire:** el oxígeno lo da la ventilación con filtro; plantas, algas y pecera aportan ~3 %.
- **Sellado:** sin ventilar, la cal sodada se acaba en días.
- **Comida:** producirla toda adentro necesitaría ~300 m² de papa bajo LED. Hay que guardar ~3.4 t de alimento seco.

El invierno nuclear en Celaya y la intensidad de la lluvia radiactiva son escenarios, no predicciones.
