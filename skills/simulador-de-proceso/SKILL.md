---
name: simulador-de-proceso
description: Use when Edu (o Mauricio) pide simular un proceso físico o químico como página web visual — pirólisis, reciclar aceite o plástico, tratamiento de agua, destilación, biodiésel, fermentación, floculación, un reactor o una planta piloto — o pide «busca todo lo que se necesita», «que las ecuaciones estén bien», «cuánto cuesta armarlo», «precios en Mercado Libre», o una idea nueva para el repo ideas-de-mauricio.
---

# Simulador de proceso

## Overview

Una idea de proceso se vuelve un **simulador web visual con modelo verificado, ecuaciones explicadas y presupuesto con precios reales**, y se sube a `ideas-de-mauricio`. Principio: **el modelo se prueba antes que la página**, y todo número que no salga de una fuente queda marcado como calibrado o de ejemplo.

Ejemplos completos en `~/ideas-de-mauricio/` (público en https://github.com/Eduardo-rico/ideas-de-mauricio):
- `pirolisis/` — reactor por lotes **dinámico** (`makeState` + `step`) con reacciones, presión y energía; plantilla para procesos con **reacción química**.
- `aceite-usado/` — tren de **etapas de separación** (`procesar` por etapas); plantilla para limpieza, destilación, floculación, adsorción. Es aceite de motor, no de cocina.

## Flujo

1. **Aclarar en una sola pregunta (AskUserQuestion, hasta 3 a la vez)** sólo lo que cambia el proceso: qué materia prima, qué producto final, qué formato. Si es obvio, no preguntes.
2. **Investigar** con WebSearch, varias búsquedas en el mismo turno, con `mode: "extended"` para datos numéricos: cinética (A, Eₐ), propiedades (Tb, M, cp, ΔH), rendimientos reportados, condiciones de operación, normas mexicanas y precios. Guarda cada URL: va en «Fuentes».
3. **Diseño preliminar:** etapas del proceso, especies o lumps, qué se conserva en cada etapa, palancas que el usuario moverá. Escala piloto realista (un tambo, 50 kg, 300 L).
4. **Modelo en `model.js`** (puro, sin DOM, entre `// MODEL-START` y `// MODEL-END`) con `escenarios.test.js`. Ver **modelado.md**.
5. **Probar y calibrar** hasta que:
   - el balance de masa cierre con error relativo `|salida/entrada − 1| < 1e-9`;
   - el de energía cuadre a ±5 % con un cálculo a mano (sensible + latente + reacción + pérdidas);
   - las tendencias sean las de la literatura;
   - los rendimientos caigan dentro del rango reportado (o a ±20 % si sólo hay un dato).
   Corrige el modelo, no la prueba.
6. **Página** con escena animada, controles en vivo, gráficas, ecuaciones MathML, tabla de parámetros etiquetada y presupuesto. Ver **pagina.md**.
7. **Presupuesto** con precios de Mercado Libre buscados en esta sesión. Ver **compras.md**.
8. **Publicar.** Archivos:
   - modelo y pruebas en `~/ideas-de-mauricio/<slug>/` (`model.js`, `escenarios.test.js`, `README.md`);
   - la página se arma en el scratchpad como `<slug>.html` (sin doctype, es lo que se publica como Artifact; antes: Artifact quickstart);
   - en el repo va como `<slug>/index.html` con doctype;
   - `check.js` y la captura se quedan en el scratchpad.
   Agrega una línea en el README raíz. Si Edu pidió subirlo al repo (lo normal en este flujo), haz commit y push a `main` y confirma con `git rev-parse` local contra `origin/main`; si no lo pidió, pregunta antes del push.

## Reglas de verdad

| Situación | Qué hacer |
|---|---|
| Valor de un artículo, patente o norma | Etiqueta `lit` y la fuente en la página |
| Valor publicado pero medido en otras condiciones (otro catalizador, aceite refinado, otra escala) | Etiqueta `lit-adaptado` y di qué cambia |
| Valor ajustado para reproducir tendencias | Etiqueta `cal` («calibrado a tendencias») |
| Dato de diseño que no encontraste (esfuerzo permitido ASME, precio de un reactivo) | Valor **de ejemplo**, marcado en la UI y en la respuesta; nunca de memoria como si fuera real |
| Precio no encontrado | «cotizar», sin inventar |
| Permisos y seguridad | Busca los de **este** proceso: residuo peligroso o de manejo especial (SEMARNAT, NOM-052), recipiente a presión (NOM-020-STPS), combustible que se vende (NOM-016-CRE, CRE), sustancias tóxicas o inflamables (metanol, solventes, ácidos), descargas de agua. No copies los de otro proyecto |

## Errores que ya pasaron (revísalos siempre)

- **Flash de una etapa para separar ligeros de un líquido pesado:** no los quita. Usa destilación diferencial (Rayleigh) o arrastre con vapor de cantidad fija.
- **Trouton para presión de vapor al vacío:** subestima la temperatura de ebullición ~80 °C. Usa Maxwell–Bonnell para fracciones de petróleo y Antoine para puros.
- **Reflujo o condensación con Psat/P sin la fracción molar:** ignora la dilución por gas o N₂. Usa un flash con Rachford–Rice.
- **Calor que entra completo al fundido:** la pared limita (h de 40–300 W/m²K). Usa dos nodos, pared y contenido, con intercambio implícito.
- **Cortes de destilación que no coinciden con los lumps:** C12 hierve a 216 °C, no a 180 °C.
- **Paso explícito en un término rígido** (válvula, intercambio de calor): hazlo implícito.
- **Masas molares redondeadas en un sistema con reacciones:** el balance no cierra. Deriva las M de la estequiometría y prueba el balance también por moles o átomos.
- **Página sin revisar:** `node --check` del script y una captura con Chrome headless antes de publicar.

## Entrega

Al final, en ≤ 10 líneas: link del Artifact, link del repo, qué enseña el modelo (3–4 hallazgos con números, incluido el costo por unidad de producto contra su precio de mercado si se encontró), cómo se verificó (pruebas, balance), qué es calibrado o de ejemplo y qué medir para quitar esa incertidumbre. El Artifact es privado: avisa que para compartirlo se usa «Compartir» o el `index.html` del repo público.
