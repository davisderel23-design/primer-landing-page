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

for ws in (fin, tr):
    for row in ws.iter_rows(min_row=2, max_row=4):
        for cell in row:
            if cell.font != INPUT_FONT and cell.column_letter != "G":
                cell.font = FONT

wb.save("mis_cuentas.xlsx")
print("OK")
