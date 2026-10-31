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
| `scripts/actualizar_datos.py` | Descarga los datos de FRED y actualiza los CSV sin borrar historial. |

## Series de FRED

| Indicador | Serie | Cálculo |
|---|---|---|
| Inflación | `CPIAUCNS` | Variación % frente al mismo mes del año anterior |
| Desempleo | `UNRATE` | Tal cual |
| Tasa de la Fed | `DFEDTARL`, `DFEDTARU` | Valor vigente al cierre de cada mes |
| Dólar | `DTWEXBGS` (índice amplio, ene 2006 = 100) | Valor al cierre de cada mes |

El DXY de ICE no está disponible gratis en FRED; por eso se usa el índice amplio de la Fed.

## Actualizar los datos a mano

```
FRED_API_KEY=tu_clave python3 scripts/actualizar_datos.py
```
Si una serie falla, su CSV no se toca y queda un aviso en `data/estado.json`.

## Verla en tu computadora

```
python3 -m http.server 8000
```
y abre http://localhost:8000

## Automatización

`.github/workflows/actualizar.yml` corre cada día a las 15:17 UTC (y con cada cambio en `main`):
descarga los datos, guarda los CSV si hay algo nuevo y publica la página en GitHub Pages.
Si una fuente falla, la página sigue con el dato anterior, muestra un aviso y la ejecución
queda en rojo para que GitHub mande un correo.

Requisitos (una sola vez): secreto `FRED_API_KEY` en Settings → Secrets and variables → Actions,
y Settings → Pages → Source: **GitHub Actions**. Solo el último dato de cada
> tarjeta coincide con las cifras de referencia; el historial se reemplazará
> con datos oficiales de FRED en la parte 2.
