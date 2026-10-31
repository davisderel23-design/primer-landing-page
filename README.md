# Economía de EE. UU. — panel de datos

Panel web sencillo (en español, pensado para el teléfono) con cuatro indicadores:
inflación, desempleo, tasa de la Fed y dólar.

## Cómo está organizado

| Archivo | Para qué sirve |
|---|---|
| `index.html` | La página. No tiene cifras escritas a mano. |
| `assets/app.js` | Lee los CSV y dibuja las tarjetas y gráficas. |
| `assets/style.css` | Colores y diseño (modo claro y oscuro). |
| `data/*.csv` | Un archivo por indicador: `periodo,etiqueta,valor` (la Fed: `periodo,etiqueta,inferior,superior`). |
| `data/estado.json` | Fecha de la última actualización y avisos. |

## Verla en tu computadora

```
python3 -m http.server 8000
```
y abre http://localhost:8000

> Estado actual: **parte 1 (datos de ejemplo)**. Solo el último dato de cada
> tarjeta coincide con las cifras de referencia; el historial se reemplazará
> con datos oficiales de FRED en la parte 2.
