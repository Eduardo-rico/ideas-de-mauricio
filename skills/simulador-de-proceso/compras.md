# Presupuesto con precios reales

## Buscar

- WebSearch modo `extended`, varias búsquedas en el mismo turno: `Mercado Libre México <artículo con especificación> precio`. Ejemplos de especificación: «resistencia de banda cerámica 220V», «válvula de alivio acero inoxidable 1/2 NPT», «bomba de vacío 2 etapas».
- Equipo grande que no hay en Mercado Libre (reactor, planta completa, destilación molecular): Alibaba, en USD, convertido con el tipo de cambio escrito como supuesto (≈ $18.5 por dólar; dilo).
- Reactivos: Mercado Libre o Amazon México; si no aparece, QuimiNet o un distribuidor, y si no hay precio, «cotizar».

## Reglas

- Sólo precios que salieron en una búsqueda de esta sesión. Anota la fecha de consulta en la página.
- Link de producto (`articulo.mercadolibre.com.mx/MLM-…`) cuando la búsqueda lo dio; si no, link de búsqueda `https://listado.mercadolibre.com.mx/<palabras-con-guiones>` con la etiqueta «Mercado Libre» y una nota de que hay varios vendedores.
- Si el artículo genérico no sirve tal cual (arrestaflamas de oxicorte, bentonita común en vez de tierra decolorante, bomba de refrigeración para vapor caliente), dilo en la descripción del renglón.
- Cantidades realistas para la escala piloto, y explica de dónde salen (7 bandas ≈ 15 kW).
- Reactivos regulados o peligrosos (metanol, sosa, ácidos, solventes): di si se venden con restricciones y agrega el equipo de protección (respirador, guantes, careta, extintor, detector de gas).

## En la página

- Tres rutas en tarjetas: **banco** (probar con 1–5 kg o L), **llave en mano** (Alibaba) y **armarla** (la tabla).
- **Equipo:** tabla por etapa con cantidad editable (`input.qty`), precio, subtotal y link; total que se recalcula.
- **Consumibles por lote:** se calculan con la configuración actual del simulador (solvente perdido, reactivo, adsorbente, kWh × tarifa editable) y dan costo por litro o kg de producto.
- **Costo por unidad de producto contra su precio de mercado** (busca el precio del diésel, del aceite base, del producto que sea), si lo encontraste.
- Nota de lo que no está y sí cuesta: instalación eléctrica, obra civil, análisis de laboratorio, trámites, gestor de residuos.
