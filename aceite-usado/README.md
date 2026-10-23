# Re-refinado de Aceite Usado

Planta piloto virtual para recuperar aceite base a partir de aceite de motor usado. Un lote (un tambo de 175 kg por defecto) pasa por cinco etapas:

1. **Sedimentación:** Stokes con gotas lognormales y viscosidad de Walther.
2. **Deshidratación:** el vapor de agua arrastra el combustible disuelto.
3. **Tratamiento químico,** con cuatro rutas:
   - Solvente polar con floculante (2-propanol + KOH).
   - Fosfato diamónico.
   - Ácido sulfúrico (histórico).
   - Ninguno.
4. **Destilación al vacío:** separación de gasóleo y evaporador de película con destilación diferencial (Rayleigh), presión de vapor de Maxwell–Bonnell y condensación fraccionada en un corte ligero (tipo SN-150) y uno pesado (tipo SN-500).
5. **Acabado:** arcilla (isoterma de Freundlich) o hidroacabado.

Calcula para cada corte la viscosidad (Refutas), el grado ISO VG, el punto de inflamación, el color, el TAN y la ceniza. También da la energía del lote, los residuos por tipo y una lista de equipo y consumibles con precio y link.

- `index.html` — la página completa; ábrela en el navegador.
- `model.js` — el modelo (17 especies, balance de masa por etapa).
- `escenarios.test.js` — 18 pruebas: `node escenarios.test.js`. Revisa que la masa cierre en 14 casos y que las tendencias sean las de la literatura.

Los parámetros marcados como «calibrado» o «típica» en la página son para comparar rutas, no para garantizar una calidad. Antes de invertir, analiza tu aceite y prueba cada ruta en el laboratorio. El aceite usado es residuo peligroso en México: hace falta autorización de la SEMARNAT.
