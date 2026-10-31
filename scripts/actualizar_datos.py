#!/usr/bin/env python3
"""
Descarga los datos nuevos de FRED y actualiza los CSV de la carpeta data/.

Reglas:
- Nunca borra el historial: las filas que ya existen se conservan; los meses
  nuevos se agregan y los meses que FRED revisó se corrigen.
- Si una fuente falla, deja su CSV tal como estaba y escribe un aviso en
  data/estado.json (la página lo muestra). El script no se detiene por eso.
- Solo toca data/estado.json cuando algo cambió, para no generar cambios vacíos.

Uso:
    FRED_API_KEY=tu_clave python3 scripts/actualizar_datos.py

La clave se lee de la variable de entorno FRED_API_KEY (en GitHub Actions viene
de un "secreto"). Nunca se escribe en ningún archivo.

Para pruebas sin internet:
    python3 scripts/actualizar_datos.py --simulado carpeta_con_json
(cada serie se lee de carpeta/<SERIE>.json con el mismo formato que da FRED).
"""

import argparse
import csv
import io
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "data"
ESTADO = DATOS / "estado.json"
DESDE = "2015-01-01"  # cuánto historial se pide a FRED

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


# ---------------------------------------------------------------- descarga

class FuenteFallo(Exception):
    pass


def descargar(serie, fuente_simulada=None, **extra):
    """Devuelve {'AAAA-MM': valor} con los datos mensuales de una serie de FRED."""
    if fuente_simulada:
        ruta = Path(fuente_simulada) / f"{serie}.json"
        if not ruta.exists():
            raise FuenteFallo(f"{serie}: no hay respuesta simulada")
        datos = json.loads(ruta.read_text())
    else:
        clave = os.environ.get("FRED_API_KEY", "").strip()
        if not clave:
            raise FuenteFallo("falta la clave FRED_API_KEY")
        params = {"series_id": serie, "api_key": clave, "file_type": "json",
                  "observation_start": DESDE, "frequency": "m", **extra}
        url = "https://api.stlouisfed.org/fred/series/observations?" + urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                datos = json.load(r)
        except Exception as e:  # red caída, clave mala, FRED fuera de servicio...
            # No se imprime la URL para no mostrar la clave en los registros
            raise FuenteFallo(f"{serie}: {type(e).__name__} {getattr(e, 'code', '')}".strip())

    resultado = {}
    for obs in datos.get("observations", []):
        valor = obs.get("value", ".")
        if valor in (".", ""):  # FRED usa "." cuando no hay dato (p. ej. un mes no publicado)
            continue
        resultado[obs["date"][:7]] = float(valor)
    if not resultado:
        raise FuenteFallo(f"{serie}: respuesta vacía")
    return resultado


# ---------------------------------------------------------------- indicadores
# Cada función devuelve {periodo: {columna: texto}} con los datos ya listos.

def revisar_rango(nombre, valores, minimo, maximo):
    malos = [v for v in valores if not (minimo <= v <= maximo)]
    if malos:
        raise FuenteFallo(f"{nombre}: valores fuera de lo razonable ({malos[:3]})")


def inflacion(sim):
    # IPC sin ajuste estacional → variación frente al mismo mes del año anterior
    ipc = descargar("CPIAUCNS", sim)
    filas = {}
    for periodo, v in ipc.items():
        a, m = periodo.split("-")
        hace_un_ano = f"{int(a) - 1}-{m}"
        if hace_un_ano in ipc:
            filas[periodo] = {"valor": f"{(v / ipc[hace_un_ano] - 1) * 100:.1f}"}
    revisar_rango("Inflación", [float(f["valor"]) for f in filas.values()], -5, 25)
    return filas


def desempleo(sim):
    tasa = descargar("UNRATE", sim)
    revisar_rango("Desempleo", tasa.values(), 0, 30)
    return {p: {"valor": f"{v:.1f}"} for p, v in tasa.items()}


def fed(sim):
    # Series diarias: se toma el valor vigente al cierre de cada mes ("eop").
    # Para el mes en curso es el valor más reciente.
    inf = descargar("DFEDTARL", sim, aggregation_method="eop")
    sup = descargar("DFEDTARU", sim, aggregation_method="eop")
    comunes = sorted(set(inf) & set(sup))
    revisar_rango("Tasa de la Fed", [inf[p] for p in comunes] + [sup[p] for p in comunes], 0, 25)
    return {p: {"inferior": f"{inf[p]:.2f}", "superior": f"{sup[p]:.2f}"} for p in comunes}


def dolar(sim):
    indice = descargar("DTWEXBGS", sim, aggregation_method="eop")
    revisar_rango("Dólar", indice.values(), 50, 250)
    return {p: {"valor": f"{v:.2f}"} for p, v in indice.items()}


INDICADORES = [
    ("Inflación", "inflacion.csv", ["valor"], inflacion),
    ("Desempleo", "desempleo.csv", ["valor"], desempleo),
    ("Tasa de la Fed", "fed.csv", ["inferior", "superior"], fed),
    ("Dólar", "dolar.csv", ["valor"], dolar),
]


# ---------------------------------------------------------------- CSV

def etiqueta(periodo):
    a, m = periodo.split("-")
    return f"{MESES[int(m) - 1]} {a}"


def leer_csv(ruta):
    if not ruta.exists():
        return {}
    with ruta.open(newline="", encoding="utf-8") as f:
        return {fila["periodo"]: fila for fila in csv.DictReader(f)}


def escribir_csv(filas, columnas):
    salida = io.StringIO()
    w = csv.writer(salida, lineterminator="\n")
    w.writerow(["periodo", "etiqueta", *columnas])
    for periodo in sorted(filas):
        w.writerow([periodo, etiqueta(periodo), *[filas[periodo][c] for c in columnas]])
    return salida.getvalue()


def fusionar(viejas, nuevas, columnas):
    """Conserva todo lo viejo; agrega meses nuevos y corrige los revisados."""
    resultado = {p: {c: f.get(c, "") for c in columnas} for p, f in viejas.items()}
    agregados, corregidos = 0, 0
    for p, f in nuevas.items():
        if p not in resultado:
            agregados += 1
        elif resultado[p] != f:
            corregidos += 1
        resultado[p] = f
    return resultado, agregados, corregidos


# ---------------------------------------------------------------- principal

def fecha_larga(d):
    return f"{d.day} de {MESES_LARGOS[d.month - 1]} de {d.year}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--simulado", help="carpeta con respuestas de FRED simuladas (para pruebas)")
    ap.add_argument("--hoy", help="fecha a usar como 'hoy' (AAAA-MM-DD), para pruebas")
    args = ap.parse_args()
    hoy = date.fromisoformat(args.hoy) if args.hoy else datetime.now(timezone.utc).date()

    estado = json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {}
    estado_antes = json.dumps(estado, sort_keys=True)
    de_ejemplo = estado.get("datos_de_ejemplo", False)
    avisos_previos = {a["indicador"]: a for a in estado.get("avisos_detalle", [])}
    avisos = {}
    hubo_cambios = False
    algun_exito = False

    for nombre, archivo, columnas, obtener in INDICADORES:
        ruta = DATOS / archivo
        try:
            nuevas = obtener(args.simulado)
        except FuenteFallo as e:
            # Se conserva el aviso más antiguo para saber desde cuándo falla
            desde = avisos_previos.get(nombre, {}).get("desde", hoy.isoformat())
            avisos[nombre] = {"indicador": nombre, "desde": desde, "detalle": str(e)}
            print(f"AVISO  {nombre}: no se pudo actualizar ({e}). Se conserva el dato anterior.")
            if os.environ.get("GITHUB_ACTIONS"):
                # Aparece como advertencia amarilla en la pantalla de GitHub Actions
                print(f"::warning title=Falló {nombre}::{e}. Se conserva el dato anterior.")
            continue

        algun_exito = True
        # La primera vez con datos reales se descartan los datos de ejemplo
        viejas = {} if de_ejemplo else leer_csv(ruta)
        filas, agregados, corregidos = fusionar(viejas, nuevas, columnas)
        texto = escribir_csv(filas, columnas)
        antes = ruta.read_text(encoding="utf-8") if ruta.exists() else ""
        if texto != antes:
            ruta.write_text(texto, encoding="utf-8")
            hubo_cambios = True
        ultimo = max(filas)
        print(f"OK     {nombre}: último dato {etiqueta(ultimo)} = {', '.join(filas[ultimo].values())} "
              f"({agregados} meses nuevos, {corregidos} corregidos)")

    if de_ejemplo and algun_exito:
        if avisos:
            # Aún quedan archivos con datos de ejemplo: se avisa en vez de borrar la marca
            for nombre in avisos:
                avisos[nombre]["detalle"] += " (sigue mostrando datos de ejemplo)"
        estado["datos_de_ejemplo"] = bool(avisos)

    if hubo_cambios:
        estado["actualizado"] = hoy.isoformat()
    estado["avisos_detalle"] = sorted(avisos.values(), key=lambda a: a["indicador"])
    estado["avisos"] = [
        f"No se pudo actualizar «{a['indicador']}» desde el {fecha_larga(date.fromisoformat(a['desde']))}. "
        "Se muestra el último dato disponible." for a in estado["avisos_detalle"]
    ]

    if json.dumps(estado, sort_keys=True) != estado_antes:
        ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("Hubo cambios en los datos." if hubo_cambios else "Sin datos nuevos.")
    salida_gh = os.environ.get("GITHUB_OUTPUT")
    if salida_gh:  # para que los pasos siguientes de GitHub Actions sepan qué pasó
        with open(salida_gh, "a", encoding="utf-8") as f:
            f.write(f"avisos={len(avisos)}\n")
    if avisos and not algun_exito:
        print("Todas las fuentes fallaron.")
    return 0  # nunca rompe la tarea: los fallos quedan como avisos


if __name__ == "__main__":
    sys.exit(main())
