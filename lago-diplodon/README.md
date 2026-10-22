# Flóculo y Diplodon

Modelo dinámico de fósforo para restaurar un lago eutrófico en dos pasos:

1. **Paso abiótico:** un floculante o inactivador de fósforo (alumbre, PAC, cloruro férrico, bentonita con lantano o Flock & Lock).
2. **Paso biótico:** siembra de la almeja nativa *Diplodon chilensis* como biofiltro.

Todo vive en un solo archivo, `modelo-lago.html`. Ahí están el simulador animado, las gráficas, el mapa dosis × densidad, el balance de fósforo, el diagrama, las ecuaciones, la tabla de parámetros y las referencias.

## Cómo reproducirlo

**En el navegador:** abre `modelo-lago.html` con doble clic. No necesita servidor ni instalar nada. Sí necesita internet para cargar las fuentes y MathJax, la librería que dibuja las ecuaciones. Sin conexión el simulador funciona igual, pero las ecuaciones se ven como texto LaTeX.

**En la terminal** (Node 18 o más reciente), con el mismo código del modelo que usa la página:

```bash
node scripts/simular.js                                   # valores por defecto
node scripts/simular.js dose=600 N0=100 wait=30           # cambia parámetros
node scripts/simular.js prod=lmb red=70 years=10          # bentonita-La, 70 % menos carga
```

Los nombres de los parámetros son los de `const P = {...}` dentro del HTML: `z`, `tau`, `Lext`, `red`, `dose`, `tF`, `rep`, `N0`, `flit`, `wait`, `CR`, `years`, etc. Los productos posibles son `alum`, `pac`, `fecl3`, `lmb` y `fl`.

## El modelo, en corto

- Es una caja bien mezclada (el lago) sobre una capa de sedimento activa.
- Tiene 9 ecuaciones diferenciales: P disuelto, fitoplancton, P móvil del sedimento, floculante en el agua, capa activa, P inactivado, densidad de *Diplodon*, residuo tóxico y P en tejido.
- Se integra con Runge–Kutta de 4.º orden con paso de 0,25 días.
- Empieza el 1 de septiembre (primavera austral), desde el estado estacional estable que deja la carga histórica, calculado con 40 años de arranque.
- El estado trófico se calcula con el índice de Carlson (1977).

## Advertencias

- Cada parámetro de la tabla está marcado como *literatura*, *calibración* o *supuesto*. Los supuestos son la toxicidad residual del floculante, la cinética de unión y la asimilación y excreción de la almeja. Hay que medirlos en el lago antes de usar el modelo para decidir.
- En estanques *Diplodon chilensis* baja mucho la clorofila (Soto & Mena 1999). En campo, su efecto sobre el fósforo total fue débil (Valdovinos et al. 2026).
- La especie es nativa de Chile y Argentina. Fuera de esa zona sería una especie introducida.

Versión publicada: https://claude.ai/code/artifact/5a19f7fd-8d31-4e7f-a251-13a721e6bc52 (privada).
