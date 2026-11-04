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
rs = wb.create_sheet("Resumen")
encabezados(rs, ["Indicador", "Valor"], [42, 18])
R = MAX_ROW
resumen = [
    ("Total de ingresos", f'=SUMIFS(Finanzas!$E$2:$E${R},Finanzas!$D$2:$D${R},"Ingreso")', MONEDA),
    ("Total de gastos", f'=SUMIFS(Finanzas!$E$2:$E${R},Finanzas!$D$2:$D${R},"Gasto")', MONEDA),
    ("Saldo", "=B2-B3", MONEDA),
    ("Número de operaciones", f"=COUNTA(Trading!$B$2:$B${R})", "0"),
    ("% de operaciones ganadoras", f'=IFERROR(COUNTIF(Trading!$G$2:$G${R},">0")/B5,0)', "0.0%"),
    ("Resultado total de trading", f"=SUM(Trading!$G$2:$G${R})", MONEDA),
    ("% de operaciones donde cumplí mis reglas", f'=IFERROR(COUNTIF(Trading!$H$2:$H${R},"Sí")/B5,0)', "0.0%"),
]
for r, (lab, f, fmt) in enumerate(resumen, start=2):
    rs[f"A{r}"] = lab
    rs[f"A{r}"].font = FONT
    rs[f"B{r}"] = f
    rs[f"B{r}"].font = FONT
    rs[f"B{r}"].number_format = fmt
rs["A10"] = "Cómo usarlo: escribe tus datos en las hojas Finanzas y Trading (texto azul = datos de ejemplo, puedes borrarlos)."
rs["A11"] = "La columna Resultado de Trading y todo este resumen se calculan solos (hasta la fila 1000)."
for c in ("A10", "A11"):
    rs[c].font = Font(name="Arial", size=9, italic=True, color="595959")

# ---------- Datos y gráficas del Resumen ----------
from openpyxl.chart import BarChart, PieChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.series import DataPoint

datos = [
    ("K1", "Datos para gráficas", None), ("L1", "Cantidad", None),
    ("K2", "Ingresos", "=B2"), ("K3", "Gastos", "=B3"),
    ("K5", "Ganadoras", f'=COUNTIF(Trading!$G$2:$G${R},">0")'),
    ("K6", "Perdedoras / empate", "=B5-L5"),
    ("K8", "Cumplí reglas", f'=COUNTIF(Trading!$H$2:$H${R},"Sí")'),
    ("K9", "No cumplí", f'=COUNTIF(Trading!$H$2:$H${R},"No")'),
]
for celda, etiqueta, formula in datos:
    rs[celda] = etiqueta
    rs[celda].font = FONT
    if formula:
        dest = "L" + celda[1:]
        rs[dest] = formula
        rs[dest].font = FONT
        rs[dest].number_format = MONEDA if celda in ("K2", "K3") else "0"
for c in ("K1", "L1"):
    rs[c].font = BOLD
    rs[c].fill = HEAD_FILL
rs.column_dimensions["K"].width = 28
rs.column_dimensions["L"].width = 14

VERDE, ROJO = "2E8B57", "C0392B"


def colorear(serie, colores):
    for i, color in enumerate(colores):
        pt = DataPoint(idx=i)
        pt.graphicalProperties.solidFill = color
        pt.graphicalProperties.line.solidFill = color
        serie.dPt.append(pt)


barras = BarChart()
barras.type = "col"
barras.title = "Ingresos vs Gastos"
barras.legend = None
barras.add_data(Reference(rs, min_col=12, min_row=2, max_row=3))
barras.set_categories(Reference(rs, min_col=11, min_row=2, max_row=3))
barras.y_axis.numFmt = '"$"#,##0'
barras.y_axis.majorGridlines = None
barras.y_axis.delete = False
barras.x_axis.delete = False
barras.dataLabels = DataLabelList()
barras.dataLabels.showVal = True
barras.dataLabels.showSerName = False
barras.dataLabels.showCatName = False
barras.dataLabels.showLegendKey = False
colorear(barras.series[0], [VERDE, ROJO])
barras.width, barras.height = 12, 7.5
rs.add_chart(barras, "A13")


def pastel(titulo, fila, ancla):
    p = PieChart()
    p.title = titulo
    p.add_data(Reference(rs, min_col=12, min_row=fila, max_row=fila + 1))
    p.set_categories(Reference(rs, min_col=11, min_row=fila, max_row=fila + 1))
    p.dataLabels = DataLabelList()
    p.dataLabels.showPercent = True
    p.dataLabels.showVal = False
    p.dataLabels.showSerName = False
    p.dataLabels.showCatName = False
    p.dataLabels.showLegendKey = False
    colorear(p.series[0], [VERDE, ROJO])
    p.width, p.height = 10, 7.5
    rs.add_chart(p, ancla)


pastel("Operaciones ganadoras vs perdedoras", 5, "D13")
pastel("¿Cumplí mis reglas?", 8, "A29")

# ---------- Gastos por categoría ----------
CATEGORIAS = ["Alimentación", "Vivienda", "Transporte", "Servicios", "Salud",
              "Ocio", "Educación", "Deudas", "Otros"]
C0 = 12  # primera fila de categorías
C1 = C0 + len(CATEGORIAS) - 1
rs[f"K{C0 - 1}"] = "Categoría de gasto"
rs[f"L{C0 - 1}"] = "Gastado"
for c in (f"K{C0 - 1}", f"L{C0 - 1}"):
    rs[c].font = BOLD
    rs[c].fill = HEAD_FILL
for i, cat in enumerate(CATEGORIAS):
    r = C0 + i
    rs[f"K{r}"] = cat
    rs[f"K{r}"].font = INPUT_FONT
    rs[f"L{r}"] = (f'=SUMIFS(Finanzas!$E$2:$E${R},Finanzas!$D$2:$D${R},"Gasto",'
                   f'Finanzas!$C$2:$C${R},K{r})')
    rs[f"L{r}"].font = FONT
    rs[f"L{r}"].number_format = MONEDA
fila_sin = C1 + 1
rs[f"K{fila_sin}"] = "Sin categoría / fuera de lista"
rs[f"K{fila_sin}"].font = FONT
rs[f"L{fila_sin}"] = f"=B3-SUM(L{C0}:L{C1})"
rs[f"L{fila_sin}"].font = FONT
rs[f"L{fila_sin}"].number_format = MONEDA
rs[f"K{fila_sin + 1}"] = "Puedes renombrar las categorías en azul."
rs[f"K{fila_sin + 1}"].font = Font(name="Arial", size=9, italic=True, color="595959")

# Lista desplegable de Categoría en Finanzas, tomada de esta tabla.
# Estilo "information": sugiere la lista pero deja escribir otras (p. ej. ingresos).
dv_cat = DataValidation(type="list", formula1=f"=Resumen!$K${C0}:$K${C1}",
                        allow_blank=True, errorStyle="information")
dv_cat.error = "Esta categoría no está en la lista; contará como 'Sin categoría' en la gráfica de gastos."
dv_cat.errorTitle = "Categoría nueva"
fin.add_data_validation(dv_cat)
dv_cat.add(f"C2:C{MAX_ROW}")

cat_chart = BarChart()
cat_chart.type = "bar"
cat_chart.title = "Gastos por categoría"
cat_chart.legend = None
cat_chart.add_data(Reference(rs, min_col=12, min_row=C0, max_row=fila_sin))
cat_chart.set_categories(Reference(rs, min_col=11, min_row=C0, max_row=fila_sin))
cat_chart.x_axis.scaling.orientation = "maxMin"  # primera categoría arriba
cat_chart.x_axis.delete = False
cat_chart.y_axis.delete = False
cat_chart.y_axis.numFmt = '"$"#,##0'
cat_chart.y_axis.majorGridlines = None
cat_chart.y_axis.crosses = "max"  # eje de montos abajo
cat_chart.dataLabels = DataLabelList()
cat_chart.dataLabels.showVal = True
cat_chart.dataLabels.showSerName = False
cat_chart.dataLabels.showCatName = False
cat_chart.dataLabels.showLegendKey = False
cat_chart.series[0].graphicalProperties.solidFill = ROJO
cat_chart.series[0].graphicalProperties.line.solidFill = ROJO
cat_chart.width, cat_chart.height = 11.5, 9
rs.add_chart(cat_chart, "D29")

# ---------- Evolución por mes (fechas) ----------
from openpyxl.chart import LineChart

M0 = 27  # primera fila de meses
rs["K25"] = "Año a graficar"
rs["K25"].font = Font(name="Arial", size=10, bold=True)
rs["L25"] = 2026
rs["L25"].font = INPUT_FONT
rs["L25"].fill = PatternFill("solid", fgColor="FFFF00")
rs["L25"].comment = Comment("Cambia el año y las gráficas por mes se actualizan.", "mis_cuentas")
for col, txt in zip("KLMNO", ["Mes", "Ingresos", "Gastos", "Resultado trading", "Trading acumulado"]):
    rs[f"{col}{M0 - 1}"] = txt
    rs[f"{col}{M0 - 1}"].font = BOLD
    rs[f"{col}{M0 - 1}"].fill = HEAD_FILL
for col in "MNO":
    rs.column_dimensions[col].width = 18
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
for m, nombre in enumerate(MESES, start=1):
    r = M0 + m - 1
    desde = f"DATE($L$25,{m},1)"
    hasta = f"DATE($L$25,{m + 1},1)"  # DATE ajusta el mes 13 a enero del año siguiente
    rs[f"K{r}"] = nombre
    for col, tipo in (("L", "Ingreso"), ("M", "Gasto")):
        rs[f"{col}{r}"] = (f'=SUMIFS(Finanzas!$E$2:$E${R},Finanzas!$D$2:$D${R},"{tipo}",'
                           f'Finanzas!$A$2:$A${R},">="&{desde},Finanzas!$A$2:$A${R},"<"&{hasta})')
    rs[f"N{r}"] = (f'=SUMIFS(Trading!$G$2:$G${R},Trading!$A$2:$A${R},">="&{desde},'
                   f'Trading!$A$2:$A${R},"<"&{hasta})')
    rs[f"O{r}"] = f"=N{r}" if m == 1 else f"=O{r - 1}+N{r}"
    for col in "KLMNO":
        rs[f"{col}{r}"].font = FONT
        if col != "K":
            rs[f"{col}{r}"].number_format = MONEDA
M1 = M0 + 11

mes_chart = BarChart()
mes_chart.type = "col"
mes_chart.title = "Ingresos y gastos por mes"
mes_chart.add_data(Reference(rs, min_col=12, max_col=13, min_row=M0 - 1, max_row=M1), titles_from_data=True)
mes_chart.set_categories(Reference(rs, min_col=11, min_row=M0, max_row=M1))
mes_chart.series[0].graphicalProperties.solidFill = VERDE
mes_chart.series[0].graphicalProperties.line.solidFill = VERDE
mes_chart.series[1].graphicalProperties.solidFill = ROJO
mes_chart.series[1].graphicalProperties.line.solidFill = ROJO
mes_chart.y_axis.numFmt = '"$"#,##0'
mes_chart.y_axis.majorGridlines = None
mes_chart.x_axis.delete = False
mes_chart.y_axis.delete = False
mes_chart.legend.position = "b"
mes_chart.width, mes_chart.height = 12, 7.5
rs.add_chart(mes_chart, "A49")

eq = LineChart()
eq.title = "Resultado de trading acumulado por mes"
eq.add_data(Reference(rs, min_col=15, min_row=M0 - 1, max_row=M1), titles_from_data=True)
eq.set_categories(Reference(rs, min_col=11, min_row=M0, max_row=M1))
eq.series[0].graphicalProperties.line.solidFill = "1F4E78"
eq.series[0].graphicalProperties.line.width = 28000
eq.series[0].marker.symbol = "circle"
eq.series[0].marker.size = 6
eq.series[0].smooth = False
eq.y_axis.numFmt = '"$"#,##0'
eq.x_axis.delete = False
eq.y_axis.delete = False
eq.legend = None
eq.width, eq.height = 11.5, 7.5
rs.add_chart(eq, "D49")

for ws in (fin, tr):
    for row in ws.iter_rows(min_row=2, max_row=4):
        for cell in row:
            if cell.font != INPUT_FONT and cell.column_letter != "G":
                cell.font = FONT

wb.save("mis_cuentas.xlsx")
print("OK")
