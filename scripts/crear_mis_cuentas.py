"""Genera mis_cuentas.xlsx con hojas Finanzas, Trading y Resumen."""
from datetime import date
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.comments import Comment

MAX_ROW = 1000
MONEDA = '"$"#,##0.00;[Red]-"$"#,##0.00;"-"'
FONT = Font(name="Arial", size=10)
BOLD = Font(name="Arial", size=10, bold=True, color="FFFFFF")
HEAD_FILL = PatternFill("solid", fgColor="1F4E78")
INPUT_FONT = Font(name="Arial", size=10, color="0000FF")

wb = Workbook()


def encabezados(ws, cols, anchos):
    for i, (c, w) in enumerate(zip(cols, anchos), start=1):
        cell = ws.cell(row=1, column=i, value=c)
        cell.font = BOLD
        cell.fill = HEAD_FILL
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[cell.column_letter].width = w
    ws.freeze_panes = "A2"


def lista(ws, opciones, rango):
    dv = DataValidation(type="list", formula1=f'"{",".join(opciones)}"', allow_blank=True)
    dv.error = "Elige una opción de la lista"
    dv.errorTitle = "Valor no válido"
    ws.add_data_validation(dv)
    dv.add(rango)


# ---------- Finanzas ----------
fin = wb.active
fin.title = "Finanzas"
encabezados(fin, ["Fecha", "Concepto", "Categoría", "Tipo", "Monto"], [12, 30, 18, 12, 14])
filas = [
    (date(2026, 11, 1), "Salario", "Trabajo", "Ingreso", 2500),
    (date(2026, 11, 2), "Supermercado", "Alimentación", "Gasto", 180.5),
    (date(2026, 11, 3), "Alquiler", "Vivienda", "Gasto", 800),
]
for r, fila in enumerate(filas, start=2):
    for c, v in enumerate(fila, start=1):
        fin.cell(row=r, column=c, value=v).font = INPUT_FONT
lista(fin, ["Ingreso", "Gasto"], f"D2:D{MAX_ROW}")
for r in range(2, MAX_ROW + 1):
    fin[f"A{r}"].number_format = "DD/MM/YYYY"
    fin[f"E{r}"].number_format = MONEDA

# ---------- Trading ----------
tr = wb.create_sheet("Trading")
encabezados(
    tr,
    ["Fecha", "Activo", "Dirección", "Precio entrada", "Precio salida",
     "Lote", "Resultado", "Cumplí reglas", "Notas"],
    [12, 14, 12, 15, 15, 10, 14, 14, 40],
)
ops = [
    (date(2026, 11, 1), "EURUSD", "Compra", 1.0850, 1.0900, 10000, "Sí", "Entrada en soporte, respeté el stop"),
    (date(2026, 11, 2), "AAPL", "Venta", 225.40, 228.10, 10, "No", "Entré sin confirmación"),
    (date(2026, 11, 3), "BTCUSD", "Compra", 68000, 69500, 0.05, "Sí", "Seguí el plan"),
]
for r, (f, a, d, pe, ps, lote, regla, nota) in enumerate(ops, start=2):
    for c, v in zip("ABCDEFHI", (f, a, d, pe, ps, lote, regla, nota)):
        tr[f"{c}{r}"] = v
        tr[f"{c}{r}"].font = INPUT_FONT
for r in range(2, MAX_ROW + 1):
    # Resultado = (salida - entrada) x lote, con signo invertido en ventas
    tr[f"G{r}"] = (
        f'=IF(OR(C{r}="",D{r}="",E{r}="",F{r}=""),"",'
        f'IF(C{r}="Compra",(E{r}-D{r})*F{r},(D{r}-E{r})*F{r}))'
    )
    tr[f"G{r}"].font = FONT
    tr[f"G{r}"].number_format = MONEDA
    tr[f"A{r}"].number_format = "DD/MM/YYYY"
    tr[f"D{r}"].number_format = "#,##0.0000"
    tr[f"E{r}"].number_format = "#,##0.0000"
tr["G1"].comment = Comment(
    "Se calcula solo: Compra = (salida - entrada) x lote; "
    "Venta = (entrada - salida) x lote. No escribas aquí.", "mis_cuentas")
lista(tr, ["Compra", "Venta"], f"C2:C{MAX_ROW}")
lista(tr, ["Sí", "No"], f"H2:H{MAX_ROW}")

# ---------- Resumen ----------
from openpyxl.chart import BarChart, PieChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.series import DataPoint

rs = wb.create_sheet("Resumen")
R = MAX_ROW
FECHA = "DD/MM/YYYY"
AMARILLO = PatternFill("solid", fgColor="FFFF00")
NOTA = Font(name="Arial", size=9, italic=True, color="595959")
VERDE, ROJO, AZUL = "2E8B57", "C0392B", "1F4E78"

for col, w in zip("ABC", (42, 20, 20)):
    rs.column_dimensions[col].width = w

rs["A1"] = "Resumen de mis cuentas"
rs["A1"].font = Font(name="Arial", size=14, bold=True, color=AZUL)


def celda(ref, valor, fuente=FONT, fmt=None):
    rs[ref] = valor
    rs[ref].font = fuente
    if fmt:
        rs[ref].number_format = fmt


# --- Selector de periodo ---
F_FIN, F_TR = f"Finanzas!$A$2:$A${R}", f"Trading!$A$2:$A${R}"
celda("A3", "Periodo (elige: Todo, Mes o Semana)", Font(name="Arial", size=10, bold=True))
celda("B3", "Mes", INPUT_FONT)
celda("A4", "Fecha de referencia", Font(name="Arial", size=10, bold=True))
celda("B4", "=TODAY()", INPUT_FONT, FECHA)
for c in ("B3", "B4"):
    rs[c].fill = AMARILLO
    rs[c].alignment = Alignment(horizontal="center")
lista(rs, ["Todo", "Mes", "Semana"], "B3")
rs["B3"].comment = Comment(
    "Mes = el mes de la fecha de referencia. Semana = la semana (lunes a domingo) "
    "de la fecha de referencia. Todo = todos tus registros.", "mis_cuentas")
rs["B4"].comment = Comment(
    "Con =HOY() ves esta semana o este mes. Escribe otra fecha para ver otra semana u otro mes.",
    "mis_cuentas")
celda("A5", "Desde")
celda("B5", f'=IF($B$3="Semana",$B$4-WEEKDAY($B$4,2)+1,IF($B$3="Mes",DATE(YEAR($B$4),MONTH($B$4),1),'
            f'IF(COUNT({F_FIN},{F_TR})=0,$B$4,MIN({F_FIN},{F_TR}))))', FONT, FECHA)
celda("A6", "Hasta")
celda("B6", f'=IF($B$3="Semana",$B$5+6,IF($B$3="Mes",DATE(YEAR($B$4),MONTH($B$4)+1,0),'
            f'IF(COUNT({F_FIN},{F_TR})=0,$B$4,MAX({F_FIN},{F_TR}))))', FONT, FECHA)
for c in ("B5", "B6"):
    rs[c].alignment = Alignment(horizontal="center")


def en_periodo(rango_fechas):
    return f'{rango_fechas},">="&$B$5,{rango_fechas},"<="&$B$6'


# --- Indicadores: periodo seleccionado y todo el historial ---
for col, txt in zip("ABC", ["Indicador", "Periodo seleccionado", "Todo el historial"]):
    celda(f"{col}8", txt, BOLD)
    rs[f"{col}8"].fill = HEAD_FILL
    rs[f"{col}8"].alignment = Alignment(horizontal="center")

FE, FD = f"Finanzas!$E$2:$E${R}", f"Finanzas!$D$2:$D${R}"
TB, TG, TH = f"Trading!$B$2:$B${R}", f"Trading!$G$2:$G${R}", f"Trading!$H$2:$H${R}"
P_F, P_T = en_periodo(F_FIN), en_periodo(F_TR)
indicadores = [
    ("Total de ingresos", f'=SUMIFS({FE},{FD},"Ingreso",{P_F})', f'=SUMIFS({FE},{FD},"Ingreso")', MONEDA),
    ("Total de gastos", f'=SUMIFS({FE},{FD},"Gasto",{P_F})', f'=SUMIFS({FE},{FD},"Gasto")', MONEDA),
    ("Saldo", "=B9-B10", "=C9-C10", MONEDA),
    ("Número de operaciones", f'=COUNTIFS({TB},"<>",{P_T})', f"=COUNTA({TB})", "0"),
    ("% de operaciones ganadoras", f'=IFERROR(COUNTIFS({TG},">0",{P_T})/B12,0)',
     f'=IFERROR(COUNTIF({TG},">0")/C12,0)', "0.0%"),
    ("Resultado total de trading", f"=SUMIFS({TG},{P_T})", f"=SUM({TG})", MONEDA),
    ("% de operaciones donde cumplí mis reglas", f'=IFERROR(COUNTIFS({TH},"Sí",{P_T})/B12,0)',
     f'=IFERROR(COUNTIF({TH},"Sí")/C12,0)', "0.0%"),
]
for r, (lab, fp, ft, fmt) in enumerate(indicadores, start=9):
    celda(f"A{r}", lab)
    celda(f"B{r}", fp, FONT, fmt)
    celda(f"C{r}", ft, FONT, fmt)

celda("A17", "Cómo usarlo: escribe tus datos en Finanzas y Trading (texto azul = ejemplos, puedes borrarlos).", NOTA)
celda("A18", "Cambia las celdas amarillas para ver otra semana o mes: las gráficas y la columna B se actualizan solas.", NOTA)

# --- Tablas auxiliares para las gráficas (columnas K en adelante) ---
rs.column_dimensions["K"].width = 30
for col in "LMNOPQ":
    rs.column_dimensions[col].width = 19


def encabezado_aux(fila, textos):
    for col, txt in zip("KLMNOPQ", textos):
        celda(f"{col}{fila}", txt, BOLD)
        rs[f"{col}{fila}"].fill = HEAD_FILL


encabezado_aux(1, ["Datos para gráficas (periodo)", "Cantidad"])
aux = [
    (2, "Ingresos", "=B9", MONEDA), (3, "Gastos", "=B10", MONEDA),
    (5, "Ganadoras", f'=COUNTIFS({TG},">0",{P_T})', "0"), (6, "Perdedoras / empate", "=B12-L5", "0"),
    (8, "Cumplí reglas", f'=COUNTIFS({TH},"Sí",{P_T})', "0"),
    (9, "No cumplí", f'=COUNTIFS({TH},"No",{P_T})', "0"),
]
for fila, lab, f, fmt in aux:
    celda(f"K{fila}", lab)
    celda(f"L{fila}", f, FONT, fmt)

# Gastos por categoría en el periodo
CATEGORIAS = ["Alimentación", "Vivienda", "Transporte", "Servicios", "Salud",
              "Ocio", "Educación", "Deudas", "Otros"]
C0 = 12
C1 = C0 + len(CATEGORIAS) - 1
encabezado_aux(C0 - 1, ["Categoría de gasto", "Gastado (periodo)"])
for i, cat in enumerate(CATEGORIAS):
    r = C0 + i
    celda(f"K{r}", cat, INPUT_FONT)
    celda(f"L{r}", f'=SUMIFS({FE},{FD},"Gasto",Finanzas!$C$2:$C${R},K{r},{P_F})', FONT, MONEDA)
SIN = C1 + 1
celda(f"K{SIN}", "Sin categoría / fuera de lista")
celda(f"L{SIN}", f"=B10-SUM(L{C0}:L{C1})", FONT, MONEDA)
celda(f"K{SIN + 1}", "Puedes renombrar las categorías en azul.", NOTA)

dv_cat = DataValidation(type="list", formula1=f"=Resumen!$K${C0}:$K${C1}",
                        allow_blank=True, errorStyle="information")
dv_cat.error = "Esta categoría no está en la lista; contará como 'Sin categoría' en la gráfica de gastos."
dv_cat.errorTitle = "Categoría nueva"
fin.add_data_validation(dv_cat)
dv_cat.add(f"C2:C{MAX_ROW}")

# Evolución: 12 semanas (si el periodo es Semana) o 12 meses del año de referencia
E0 = 26
celda(f"K{E0 - 2}", "Evolución: últimas 12 semanas si el periodo es Semana; meses del año si es Mes o Todo.", NOTA)
encabezado_aux(E0 - 1, ["Periodo", "Ingresos", "Gastos", "Resultado trading",
                        "Trading acumulado", "Inicio", "Fin"])
MESES = '"Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"'
for i in range(1, 13):
    r = E0 + i - 1
    celda(f"P{r}", f'=IF($B$3="Semana",$B$4-WEEKDAY($B$4,2)+1-7*{12 - i},DATE(YEAR($B$4),{i},1))',
          FONT, FECHA)
    celda(f"Q{r}", f'=IF($B$3="Semana",P{r}+6,DATE(YEAR($B$4),{i + 1},0))', FONT, FECHA)
    celda(f"K{r}", f'=IF($B$3="Semana","Sem "&DAY(P{r})&"/"&MONTH(P{r}),CHOOSE(MONTH(P{r}),{MESES}))')
    rango_f = f'{F_FIN},">="&P{r},{F_FIN},"<="&Q{r}'
    celda(f"L{r}", f'=SUMIFS({FE},{FD},"Ingreso",{rango_f})', FONT, MONEDA)
    celda(f"M{r}", f'=SUMIFS({FE},{FD},"Gasto",{rango_f})', FONT, MONEDA)
    celda(f"N{r}", f'=SUMIFS({TG},{F_TR},">="&P{r},{F_TR},"<="&Q{r})', FONT, MONEDA)
    celda(f"O{r}", f"=N{r}" if i == 1 else f"=O{r - 1}+N{r}", FONT, MONEDA)
E1 = E0 + 11


# --- Gráficas ---
def colorear(serie, colores):
    for i, color in enumerate(colores):
        pt = DataPoint(idx=i)
        pt.graphicalProperties.solidFill = color
        pt.graphicalProperties.line.solidFill = color
        serie.dPt.append(pt)


def etiquetas(chart, valor=True, porcentaje=False):
    chart.dataLabels = DataLabelList()
    chart.dataLabels.showVal = valor
    chart.dataLabels.showPercent = porcentaje
    chart.dataLabels.showSerName = False
    chart.dataLabels.showCatName = False
    chart.dataLabels.showLegendKey = False


def ejes(chart, formato='"$"#,##0'):
    chart.x_axis.delete = False
    chart.y_axis.delete = False
    chart.y_axis.numFmt = formato


barras = BarChart()
barras.type = "col"
barras.title = "Ingresos vs Gastos (periodo)"
barras.legend = None
barras.add_data(Reference(rs, min_col=12, min_row=2, max_row=3))
barras.set_categories(Reference(rs, min_col=11, min_row=2, max_row=3))
barras.y_axis.majorGridlines = None
ejes(barras)
etiquetas(barras)
colorear(barras.series[0], [VERDE, ROJO])
barras.width, barras.height = 14, 7.5
rs.add_chart(barras, "A20")


def pastel(titulo, fila, ancla):
    p = PieChart()
    p.title = titulo
    p.add_data(Reference(rs, min_col=12, min_row=fila, max_row=fila + 1))
    p.set_categories(Reference(rs, min_col=11, min_row=fila, max_row=fila + 1))
    etiquetas(p, valor=False, porcentaje=True)
    colorear(p.series[0], [VERDE, ROJO])
    p.width, p.height = 11.5, 7.5
    rs.add_chart(p, ancla)


pastel("Ganadoras vs perdedoras (periodo)", 5, "D20")

cat_chart = BarChart()
cat_chart.type = "bar"
cat_chart.title = "Gastos por categoría (periodo)"
cat_chart.legend = None
cat_chart.add_data(Reference(rs, min_col=12, min_row=C0, max_row=SIN))
cat_chart.set_categories(Reference(rs, min_col=11, min_row=C0, max_row=SIN))
cat_chart.x_axis.scaling.orientation = "maxMin"  # primera categoría arriba
cat_chart.y_axis.crosses = "max"  # eje de montos abajo
cat_chart.y_axis.majorGridlines = None
ejes(cat_chart)
etiquetas(cat_chart)
cat_chart.series[0].graphicalProperties.solidFill = ROJO
cat_chart.series[0].graphicalProperties.line.solidFill = ROJO
cat_chart.width, cat_chart.height = 14, 9
rs.add_chart(cat_chart, "A36")

pastel("¿Cumplí mis reglas? (periodo)", 8, "D36")

evo = BarChart()
evo.type = "col"
evo.title = "Ingresos y gastos: semana a semana / mes a mes"
evo.add_data(Reference(rs, min_col=12, max_col=13, min_row=E0 - 1, max_row=E1), titles_from_data=True)
evo.set_categories(Reference(rs, min_col=11, min_row=E0, max_row=E1))
for serie, color in zip(evo.series, (VERDE, ROJO)):
    serie.graphicalProperties.solidFill = color
    serie.graphicalProperties.line.solidFill = color
evo.y_axis.majorGridlines = None
ejes(evo)
evo.legend.position = "b"
evo.width, evo.height = 14, 7.5
rs.add_chart(evo, "A55")

eq = LineChart()
eq.title = "Trading acumulado: semana a semana / mes a mes"
eq.add_data(Reference(rs, min_col=15, min_row=E0 - 1, max_row=E1), titles_from_data=True)
eq.set_categories(Reference(rs, min_col=11, min_row=E0, max_row=E1))
eq.series[0].graphicalProperties.line.solidFill = AZUL
eq.series[0].graphicalProperties.line.width = 28000
eq.series[0].marker.symbol = "circle"
eq.series[0].marker.size = 6
eq.series[0].smooth = False
ejes(eq)
eq.legend = None
eq.width, eq.height = 11.5, 7.5
rs.add_chart(eq, "D55")

for ws in (fin, tr):
    for row in ws.iter_rows(min_row=2, max_row=4):
        for cell in row:
            if cell.font != INPUT_FONT and cell.column_letter != "G":
                cell.font = FONT

wb.save("mis_cuentas.xlsx")
print("OK")
