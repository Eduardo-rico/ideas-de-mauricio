# La página del simulador

Antes de escribirla: `Artifact` con `action: "quickstart"` e `intent: "other"` (trae el contrato de la página). Copia la estructura de `aceite-usado/index.html` o `pirolisis/index.html`.

## Partes, en este orden

1. **Encabezado:** eyebrow con la escala, título de 2–4 palabras, una frase de qué hace, botones Arrancar/Pausar, Ir al final, Reiniciar y velocidad.
2. **Pills de estado:** etapa actual y avisos (inflamable, residuo peligroso, presión alta, no cumple especificación).
3. **Seis tiles** con los números que importan (tiempo, temperatura o etapa, producto en kg y %, calidad, energía, residuos).
4. **Escena en canvas 1000×620** con los equipos dibujados como diagrama de proceso:
   - el líquido cambia de color con su calidad;
   - partículas por las tuberías con el color de cada especie y frecuencia proporcional al flujo;
   - gotas, burbujas, flóculos, flamas, rotores y medidores animados;
   - tanques de producto y botes de residuo que se llenan.
   Al lado, el panel de controles por etapa con escenarios de un clic; los controles de proceso cambian en vivo, y los de carga se aplican al reiniciar.
5. **Tres gráficas** (canvas propio, sin librerías): una dinámica contra el tiempo o por etapa, el destino de cada kg, y la calidad contra una referencia con pills de cumple / no cumple.
6. **Bitácora** de corridas terminadas para comparar condiciones.
7. **Ecuaciones** en MathML (el navegador lo dibuja sin librerías), cada una con una explicación de 2–3 líneas con un número del propio modelo.
8. **Tabla de parámetros** con etiquetas `lit` (verde) y `cal` (ámbar), y una nota de qué medir para quitar lo calibrado.
9. **Presupuesto** (ver compras.md), **permisos y seguridad**, **fuentes** con links.

## Técnica

- Colores como tokens en `:root` con tema oscuro y claro; el canvas lee los tokens con `getComputedStyle` y se vuelve a leer al cambiar de tema.
- `setupCanvas` con devicePixelRatio ≤ 2; escena escalada a 1000×620.
- Un `requestAnimationFrame`: avanza el modelo, actualiza tiles, estado, escena y gráficas.
- Nada de `alert`, `confirm` ni descargas; links con `target="_blank"`.

## Revisar antes de publicar

```bash
python3 -c "import re;s=open('<slug>.html').read();open('check.js','w').write('\n'.join(re.findall(r'<script>(.*?)</script>',s,re.S)).replace('document','__d'))" && node --check check.js
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --window-size=1400,2200 --virtual-time-budget=4000 --screenshot=$PWD/shot.png "file://$PWD/preview.html"
```

Corre esto en el scratchpad. `preview.html` es `<slug>.html` envuelta en `<!doctype html><html><head>…</head><body>…</body></html>`; esa misma versión es el `index.html` del repo. Mira la captura una vez, corrige en una pasada (rellenos que heredan `fillStyle`, etiquetas encimadas, columnas anchas) y publica.
