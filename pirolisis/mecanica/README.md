# Hoja mecánica y de seguridad del reactor

Espesor del recipiente, válvula de alivio y cuánto calor acepta el plástico por la pared. Sin dependencias, solo Python.

```bash
cd pirolisis/mecanica
uv run python hoja.py                                   # reactor de 300 L del simulador
uv run python hoja.py --V 1.0 --P 4 --S 95 --potencia 80
uv run python hoja.py --ayuda-S                         # de dónde sale el esfuerzo permitido
uv run pytest                                           # 9 pruebas, incluido el ejemplo resuelto de API 520
```

## Resultado para el reactor de 300 L (con esfuerzos de EJEMPLO)

| | Resultado |
|---|---|
| Geometría | Ø 593 mm, casco de 889 mm, tapas elipsoidales 2:1, 1.41 m² mojados al 60 % |
| Espesor a 6 barg y 550 °C (ASME VIII Div. 1, UG-27 y UG-32) | 2.7 mm calculado + 3 mm de corrosión → lámina de 6 mm en casco y tapas |
| Presión máxima de trabajo / prueba hidrostática | 6.8 barg / 12.7 barg |
| Vacío | aguanta vacío total (orientativo) |
| Válvula de alivio (API 520/521) | rige el incendio: 688 kg/h → 118 mm² → orificio **E** de API 526 |
| Calor por la pared | **2–8 kW** con el plástico recién fundido (1–100 Pa·s) y 37 kW con aceite craqueado, contra 40 kW del calentador |

El punto más importante es el último: **el reactor queda limitado por transferencia de calor, no por la cinética.** El plástico fundido es tan viscoso que la pared apenas le pasa calor al principio del lote. Las plantas reales lo resuelven así:
- **Cargar sobre aceite o cera caliente** que quedó del lote anterior: baja la viscosidad desde el inicio.
- **Más área de calentamiento:** serpentines internos o un reactor más esbelto.
- **Pared más caliente,** con más coque pegado y menos resistencia del acero.
- **Reactores continuos** de tornillo o lecho fluidizado.

## Qué calcula

1. **Espesores por ASME VIII Div. 1:**
   - Casco circunferencial y longitudinal (UG-27).
   - Tapa elipsoidal 2:1 (UG-32(d)).
   - Mínimo de UG-16(b), sobreespesor de corrosión, lámina comercial.
   - Presión máxima de trabajo con las láminas ya corroídas y prueba hidrostática de 1.3 × MAWP × S_amb/S (UG-99).
2. **Vacío:** pandeo elástico de Windenburg–Trilling con factor 3. Es orientativo; el código usa las gráficas de UG-28. Importa porque al enfriarse el vapor condensa y el reactor puede jalar vacío.
3. **Válvula de alivio:**
   - Escenarios de API 521:
     - Salida bloqueada: el condensador tapado con cera, con el calentador a toda potencia.
     - Incendio: Q = 43 200·F·A^0.82 W.
     - Regulador de N₂ que falla abierto.
   - Área por API 520 Parte I en flujo crítico, con Kc = 0.9 si hay disco de ruptura. Se recomienda poner disco: la cera puede tapar la válvula.
   - Se elige el orificio estándar de API 526.
4. **Calor por la pared:**
   - Agitador de ancla con la correlación de Uhl y Gray, Nu = 0.36 Re^(2/3) Pr^(1/3).
   - Se calcula para varias viscosidades, porque el fundido pasa de ~100 Pa·s a ~0.01 Pa·s conforme se craquea.
   - Abajo de Re = 300 la correlación se extrapola y la hoja lo marca.

## Antes de usarlo para fabricar

- **Esfuerzos permitidos:** los valores por defecto (80 MPa a 550 °C, 115 MPa a temperatura ambiente) son de ejemplo. Toma los reales de ASME Sección II Parte D, Tabla 1A, para tu material y tu edición (`--ayuda-S`). Para 500–550 °C se usa normalmente 316/316H, 321H o 310S; los grados «L» tienen límite de temperatura más bajo.
- **Lo que esta hoja no cubre:** boquillas y sus refuerzos (UG-37), bridas, soportes, cargas de viento y sismo, fatiga por ciclos de calentamiento, ni termofluencia de largo plazo.
- **En México:**
  - El recipiente cae en la NOM-020-STPS-2011: necesita expediente, prueba de presión y dictamen de una unidad de verificación.
  - El diseño y la fabricación los firma un ingeniero con la responsabilidad legal.
