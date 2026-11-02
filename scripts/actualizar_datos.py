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
DESDE = "2005-01-01"  # cuánto historial se pide a FRED (2006 es la base del índice del dólar)

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


# ---------------------------------------------------------------- descarga

class FuenteFallo(Exception):
    pass


_YA_DESCARGADO = {}  # para no pedir dos veces la misma serie en una corrida


def descargar(serie, fuente_simulada=None, diaria=False):
    clave_cache = (serie, diaria)
    if clave_cache not in _YA_DESCARGADO:
        _YA_DESCARGADO[clave_cache] = _descargar(serie, fuente_simulada, diaria)
    return _YA_DESCARGADO[clave_cache]


def _descargar(serie, fuente_simulada=None, diaria=False):
    """Devuelve {'AAAA-MM': valor} con los datos mensuales de una serie de FRED.

    diaria=True: se piden los datos día por día y se toma el último de cada mes.
    Así el mes en curso muestra el dato más reciente (FRED, al resumir por mes,
    no entrega el mes hasta que termina)."""
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
                  "observation_start": DESDE}
        if not diaria:
            params["frequency"] = "m"
        url = "https://api.stlouisfed.org/fred/series/observations?" + urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                datos = json.load(r)
        except Exception as e:  # red caída, clave mala, FRED fuera de servicio...
            # No se imprime la URL para no mostrar la clave en los registros
            raise FuenteFallo(f"{serie}: {type(e).__name__} {getattr(e, 'code', '')}".strip())

    resultado = {}
    # Ordenadas por fecha: si hay varios datos en un mes, queda el último
    for obs in sorted(datos.get("observations", []), key=lambda o: o.get("date", "")):
        valor = obs.get("value", ".")
        if valor in (".", ""):  # FRED usa "." cuando no hay dato (p. ej. un mes no publicado)
            continue
        resultado[obs["date"][:7]] = float(valor)
    if not resultado:
        raise FuenteFallo(f"{serie}: respuesta vacía")
    return resultado


def info_serie(serie, fuente_simulada=None):
    """Datos de la serie en FRED: sobre todo 'last_updated', la fecha en que FRED
    cargó la versión revisada más reciente. Si falla, devuelve None (no es grave)."""
    if fuente_simulada:
        ruta = Path(fuente_simulada) / f"{serie}_info.json"
        return json.loads(ruta.read_text()) if ruta.exists() else None
    clave = os.environ.get("FRED_API_KEY", "").strip()
    if not clave:
        return None
    url = "https://api.stlouisfed.org/fred/series?" + urllib.parse.urlencode(
        {"series_id": serie, "api_key": clave, "file_type": "json"})
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return (json.load(r).get("seriess") or [None])[0]
    except Exception:
        return None


# ---------------------------------------------------------------- indicadores
# Cada función devuelve {periodo: {columna: texto}} con los datos ya listos.

def revisar_rango(nombre, valores, minimo, maximo):
    malos = [v for v in valores if not (minimo <= v <= maximo)]
    if malos:
        raise FuenteFallo(f"{nombre}: valores fuera de lo razonable ({malos[:3]})")


def variacion_anual(indice):
    """{periodo: nivel} → {periodo: % frente al mismo mes del año anterior}."""
    resultado = {}
    for periodo, v in indice.items():
        a, m = periodo.split("-")
        hace_un_ano = f"{int(a) - 1}-{m}"
        if hace_un_ano in indice:
            resultado[periodo] = (v / indice[hace_un_ano] - 1) * 100
    return resultado


def variacion_mensual(indice):
    """{periodo: nivel} → {periodo: % frente al mes anterior}."""
    resultado = {}
    for periodo, v in indice.items():
        a, m = map(int, periodo.split("-"))
        anterior = f"{a - 1}-12" if m == 1 else f"{a}-{m - 1:02d}"
        if anterior in indice:
            resultado[periodo] = (v / indice[anterior] - 1) * 100
    return resultado


def general_y_subyacente(nombre, anual_general, anual_sub, mensual_general, mensual_sub, sim):
    """Variación anual (y/y) y mensual (m/m) de la inflación general y subyacente.

    La anual y la mensual pueden venir de series distintas: el BLS calcula la
    anual del CPI sin ajuste estacional y la mensual con ajuste estacional."""
    general = variacion_anual(descargar(anual_general, sim))
    subyacente = variacion_anual(descargar(anual_sub, sim))
    m_general = variacion_mensual(descargar(mensual_general, sim))
    m_sub = variacion_mensual(descargar(mensual_sub, sim))
    revisar_rango(nombre, list(general.values()) + list(subyacente.values()), -5, 25)
    revisar_rango(nombre + " mensual", list(m_general.values()) + list(m_sub.values()), -5, 5)
    texto = lambda d, p: f"{d[p]:.1f}" if p in d else ""
    return {
        p: {
            "valor": f"{v:.1f}",
            "subyacente": texto(subyacente, p),
            "mensual": texto(m_general, p),
            "mensual_sub": texto(m_sub, p),
        }
        for p, v in general.items()
    }


def inflacion(sim):
    # CPI general y subyacente (sin alimentos ni energía).
    # Anual (y/y): series sin ajuste estacional, como la cifra anual que publica el BLS.
    # Mensual (m/m): series con ajuste estacional, como la cifra mensual del BLS.
    return general_y_subyacente("Inflación (IPC)", "CPIAUCNS", "CPILFENS", "CPIAUCSL", "CPILFESL", sim)


def pce(sim):
    """Índice de precios PCE general (PCEPI) y subyacente (PCEPILFE), de la BEA vía FRED.

    Todo sale de UNA sola descarga de cada serie, en su versión más reciente
    (FRED entrega por defecto la última revisión). Con esos índices se calculan
    la variación anual y la mensual, y los índices se guardan en el CSV para
    poder comprobar cada porcentaje. El archivo se reescribe completo en cada
    corrida, para que nunca queden mezclados datos de versiones distintas."""
    general = descargar("PCEPI", sim)
    sub = descargar("PCEPILFE", sim)
    revisar_rango("Inflación PCE (índices)", list(general.values()) + list(sub.values()), 10, 1000)
    a_gen, a_sub = variacion_anual(general), variacion_anual(sub)
    m_gen, m_sub = variacion_mensual(general), variacion_mensual(sub)
    revisar_rango("Inflación PCE", list(a_gen.values()) + list(a_sub.values()), -5, 25)
    revisar_rango("Inflación PCE mensual", list(m_gen.values()) + list(m_sub.values()), -5, 5)
    texto = lambda d, p, dec=1: f"{d[p]:.{dec}f}" if p in d else ""
    return {
        p: {
            "valor": texto(a_gen, p),
            "subyacente": texto(a_sub, p),
            "mensual": texto(m_gen, p),
            "mensual_sub": texto(m_sub, p),
            "indice_general": texto(general, p, 3),
            "indice_sub": texto(sub, p, 3),
        }
        for p in sorted(set(a_gen) & set(a_sub))
    }


def empleo(sim):
    # Nóminas no agrícolas (NFP): empleos creados cada mes = total del mes − total del mes anterior
    total = descargar("PAYEMS", sim)  # en miles de personas
    filas = {}
    for periodo, v in total.items():
        a, m = map(int, periodo.split("-"))
        anterior = f"{a - 1}-12" if m == 1 else f"{a}-{m - 1:02d}"
        if anterior in total:
            filas[periodo] = {"valor": f"{v - total[anterior]:.0f}"}
    revisar_rango("Empleo (NFP)", [float(f["valor"]) for f in filas.values()], -25000, 25000)
    return filas


def ipc_indice(sim):
    # Nivel del IPC (no la variación): sirve para calcular el poder de compra del dólar
    ipc = descargar("CPIAUCNS", sim)
    revisar_rango("IPC", ipc.values(), 50, 2000)
    return {p: {"valor": f"{v:.3f}"} for p, v in ipc.items()}


def desempleo(sim):
    tasa = descargar("UNRATE", sim)
    revisar_rango("Desempleo", tasa.values(), 0, 30)
    return {p: {"valor": f"{v:.1f}"} for p, v in tasa.items()}


def fed(sim):
    # Series diarias: se toma el último valor de cada mes.
    # Para el mes en curso es el valor más reciente.
    inf = descargar("DFEDTARL", sim, diaria=True)
    sup = descargar("DFEDTARU", sim, diaria=True)
    comunes = sorted(set(inf) & set(sup))
    revisar_rango("Tasa de la Fed", [inf[p] for p in comunes] + [sup[p] for p in comunes], 0, 25)
    return {p: {"inferior": f"{inf[p]:.2f}", "superior": f"{sup[p]:.2f}"} for p in comunes}


def dolar(sim):
    indice = descargar("DTWEXBGS", sim, diaria=True)
    revisar_rango("Dólar", indice.values(), 50, 250)
    return {p: {"valor": f"{v:.2f}"} for p, v in indice.items()}


INDICADORES = [
    ("Inflación", "inflacion.csv", ["valor", "subyacente", "mensual", "mensual_sub"], inflacion),
    ("Inflación PCE", "pce.csv",
     ["valor", "subyacente", "mensual", "mensual_sub", "indice_general", "indice_sub"], pce,
     {"reemplazar": True, "series": ["PCEPI", "PCEPILFE"], "fuente": "BEA vía FRED (Fed de St. Louis)"}),
    ("Empleo (NFP)", "empleo.csv", ["valor"], empleo),
    ("Desempleo", "desempleo.csv", ["valor"], desempleo),
    ("Tasa de la Fed", "fed.csv", ["inferior", "superior"], fed),
    ("Dólar", "dolar.csv", ["valor"], dolar),
    ("Poder de compra", "ipc_indice.csv", ["valor"], ipc_indice),
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

def filas_cambiadas(previas, nuevas, columnas):
    """Meses cuyo valor cambió respecto del archivo anterior (en cualquier columna que ya existía)."""
    for p, f in nuevas.items():
        vieja = previas.get(p)
        if vieja is None:
            continue
        if any(c in vieja and vieja[c] != f.get(c, "") for c in columnas):
            yield p


def registrar_fuente(estado, nombre, opciones, sim):
    """Guarda en estado.json de dónde salen los datos y la fecha de la versión revisada."""
    fuentes = estado.setdefault("fuentes", {})
    previo = fuentes.get(nombre, {})
    versiones = dict(previo.get("versiones", {}))
    for serie in opciones["series"]:
        info = info_serie(serie, sim)
        if info and info.get("last_updated"):
            versiones[serie] = info["last_updated"]
    fuentes[nombre] = {"fuente": opciones["fuente"], "series": opciones["series"], "versiones": versiones}


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

    for nombre, archivo, columnas, obtener, *extra in INDICADORES:
        opciones = extra[0] if extra else {}
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
        # Con "reemplazar", el archivo queda exactamente igual a la descarga de hoy
        # (versión más reciente de FRED), sin filas de descargas anteriores
        viejas = {} if de_ejemplo or opciones.get("reemplazar") else leer_csv(ruta)
        if opciones.get("reemplazar"):
            previas = leer_csv(ruta)
            cambiados = sorted(p for p in filas_cambiadas(previas, nuevas, columnas))
            if cambiados:
                print(f"       {nombre}: meses con valores distintos a la versión anterior: "
                      + ", ".join(etiqueta(p) for p in cambiados))
        if opciones.get("series"):
            registrar_fuente(estado, nombre, opciones, args.simulado)
        filas, agregados, corregidos = fusionar(viejas, nuevas, columnas)
        texto = escribir_csv(filas, columnas)
        antes = ruta.read_text(encoding="utf-8") if ruta.exists() else ""
        if texto != antes:
            ruta.write_text(texto, encoding="utf-8")
            hubo_cambios = True
        ultimo = max(filas)
        detalle = ("archivo reescrito completo con la versión más reciente" if opciones.get("reemplazar")
                   else f"{agregados} meses nuevos, {corregidos} corregidos")
        print(f"OK     {nombre}: último dato {etiqueta(ultimo)} = {', '.join(filas[ultimo].values())} ({detalle})")

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
