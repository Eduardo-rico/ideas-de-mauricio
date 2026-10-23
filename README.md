# Ideas de Mauricio

## Pirólisis a Combustibles (`pirolisis/`)

Planta piloto virtual que convierte plástico (PEAD, PEBD, PP, PS) en gasolina, diésel, ceras, gas y coque en un reactor por lotes. Simula en tiempo real balance de masa, presión (gas ideal + válvula de contrapresión y PSV) y energía, con diagrama animado, gráficas y la lista de equipo para armar la planta.

- `pirolisis/index.html` — la página completa; ábrela en el navegador, no necesita servidor.
- `pirolisis/model.js` — el modelo matemático solo (el mismo que trae la página).
- `pirolisis/ajuste/` — ajuste de la cinética con datos propios de TGA y reactor de banco (Python). Ver su README.
- `pirolisis/termo/` — Peng–Robinson con pseudocomponentes: deflegmador, condensador, cortes, presión de vapor y receta para DWSIM. Ver su README.
- `pirolisis/mecanica/` — espesor ASME VIII, válvula de alivio API 520/521 y calor por la pared. Ver su README.
- `pirolisis/escenarios.test.js` — corre escenarios de prueba: `cd pirolisis && node escenarios.test.js`.

El modelo es de lumps y semicuantitativo: sirve para aprender y comparar condiciones, no para dimensionar equipo. La cinética del PEAD y PP viene de Bockhorn (1999); las selectividades y el craqueo secundario están calibrados a tendencias de la literatura. Las fuentes están al final de la página.

## Búnker Celaya (`bunker-celaya/`)

Soporte de vida de un búnker para 5 personas y 4 perros durante 3 años de invierno nuclear en Celaya: radiación, aire, agua, comida, energía y cultivos (hidroponía, aeroponía, algas, pecera), hora por hora, con presupuesto. Hecho con el skill `simulador-de-proceso`. Ver `bunker-celaya/README.md`.

## Skill para hacer más simuladores (`skills/`)

`skills/simulador-de-proceso/` le enseña a Claude Code a repetir este trabajo con cualquier proceso: investigar, diseñar, sacar y probar las ecuaciones, armar la página y cotizar en Mercado Libre. Ver `skills/README.md` para instalarlo.

## Re-refinado de Aceite Usado (`aceite-usado/`)

Recuperar aceite base del aceite de motor usado: sedimentación, deshidratación, tratamiento con solvente y floculante, fosfato o ácido, destilación al vacío y acabado con arcilla o hidroacabado. Simulador visual, ecuaciones, calidad contra referencia, equipo y consumibles con precios. Ver `aceite-usado/README.md`.

## Flóculo y Diplodon (`lago-diplodon/`)

Modelo dinámico de fósforo para quitar la eutrofia de un lago en dos pasos: floculante (alumbre, PAC, FeCl₃, bentonita-La, Flock & Lock) y siembra de la almeja *Diplodon chilensis*. 9 ecuaciones diferenciales integradas con RK4, lagos animados, gráficas y referencias.

- `lago-diplodon/modelo-lago.html` — el simulador completo; ábrelo en el navegador.
- `lago-diplodon/scripts/simular.js` — corre el mismo modelo en la terminal: `cd lago-diplodon && node scripts/simular.js`.
- Detalle en `lago-diplodon/README.md`.
