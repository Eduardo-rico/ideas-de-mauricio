# Receta para DWSIM: tren de separación de la pirólisis

Generada por `diagrama.py`. Arma esto en DWSIM (Mac, Windows o Linux, gratis en dwsim.org) y compara con los números de abajo.

## 1. Paquete de propiedades

Peng–Robinson (PR). k_ij = 0.08 entre N₂ o H₂ y los hidrocarburos; los demás en 0.

## 2. Compuestos

Del banco de datos de DWSIM:

- Nitrogen (Nitrógeno)
- Hydrogen (Hidrógeno)
- Methane (Metano)
- Ethylene (Etileno)
- Ethane (Etano)
- Propylene (Propileno)
- Propane (Propano)
- 1-Butene (1-Buteno)
- N-butane (n-Butano)

Pseudocomponentes: Herramientas → Caracterización de petróleo → «Hipotéticos» con estos datos (o captura tu destilación simulada en «Petroleum Assay Manager» y deja que DWSIM los genere):

| Nombre | Tb (°C) | SG | M (g/mol) | Tc (°C) | Pc (bar) | ω |
|---|---|---|---|---|---|---|
| C5-C6 | 52.5 | 0.6695 | 78.3 | 220.6 | 33.21 | 0.2497 |
| C7-C8 | 112.1 | 0.7081 | 107.5 | 286.5 | 26.39 | 0.3364 |
| C9-C10 | 162.5 | 0.7377 | 136.8 | 339.3 | 21.96 | 0.4137 |
| C11-C12 | 206.2 | 0.7616 | 166.0 | 383.2 | 18.88 | 0.4843 |
| C13-C14 | 244.6 | 0.7814 | 195.0 | 420.5 | 16.62 | 0.5498 |
| C15-C16 | 278.8 | 0.7982 | 223.8 | 452.9 | 14.91 | 0.6112 |
| C17-C18 | 309.5 | 0.8128 | 252.4 | 481.3 | 13.58 | 0.6693 |
| C19-C22 | 349.8 | 0.8311 | 294.2 | 517.9 | 12.06 | 0.7502 |
| C23-C27 | 402.0 | 0.8537 | 356.6 | 564.0 | 10.44 | 0.9415 |
| C28-C32 | 449.8 | 0.8734 | 423.2 | 605.3 | 9.22 | 1.0479 |
| C33-C40 | 496.9 | 0.8920 | 499.2 | 645.2 | 8.21 | 1.1491 |

## 3. Corriente de alimentación «Vapor del reactor»

T = 460 °C, P = 1.20 bar abs. Flujos molares:

| Compuesto | mol/h | kg/h |
|---|---|---|
| Nitrógeno | 18.000 | 0.5043 |
| Hidrógeno | 8.929 | 0.0180 |
| Metano | 16.830 | 0.2700 |
| Etileno | 9.624 | 0.2700 |
| Etano | 8.381 | 0.2520 |
| Propileno | 10.694 | 0.4500 |
| Propano | 4.082 | 0.1800 |
| 1-Buteno | 4.171 | 0.2340 |
| n-Butano | 2.168 | 0.1260 |
| C5-C6 | 12.451 | 0.9750 |
| C7-C8 | 9.066 | 0.9750 |
| C9-C10 | 7.129 | 0.9750 |
| C11-C12 | 5.875 | 0.9750 |
| C13-C14 | 8.077 | 1.5750 |
| C15-C16 | 7.036 | 1.5750 |
| C17-C18 | 6.240 | 1.5750 |
| C19-C22 | 5.353 | 1.5750 |
| C23-C27 | 2.804 | 1.0000 |
| C28-C32 | 2.363 | 1.0000 |
| C33-C40 | 2.003 | 1.0000 |

## 4. Equipos

1. **Deflegmador:** «Separador gas–líquido» con especificación de temperatura 280.0 °C y misma presión. Su líquido es el reflujo al reactor.
2. **Condensador:** «Enfriador» a 30 °C seguido de un «Separador gas–líquido». El vapor va a la antorcha y el líquido es el aceite crudo.
3. **Destilación:** «Columna corta (Shortcut)» con clave ligera la primera fracción arriba de 180 °C y clave pesada la última abajo, o una columna rigurosa si quieres los productos con especificación real.

## 5. Resultados de referencia (Peng–Robinson en Python)

- Deflegmador: retira 2.36 kW; regresa ceras 80.8 %, diésel 11.8 %, gasolina 0.9 %
- Condensador: 2.61 kW; gasolina perdida en el gas 11.3 %
- Aceite: 9.69 kg/h con 1.4 % de gas disuelto

DWSIM debe dar lo mismo con una diferencia de pocos por ciento (usa sus propias correlaciones para Cp de gas ideal).
