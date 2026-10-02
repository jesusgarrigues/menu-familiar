"""Genera un PDF de ejemplo con formato de calendario (para pruebas)."""
import calendar
import sys
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

MENUS = [
    ("Lentejas estofadas con verduras", "Tortilla de patata con ensalada", "Fruta de temporada", "Pescado y verdura"),
    ("Crema de calabacín", "Pollo asado con patatas", "Yogur", "Huevo y ensalada"),
    ("Macarrones con tomate", "Merluza a la romana con lechuga", "Fruta", "Carne blanca y verdura"),
    ("Arroz a la cubana", "Filete de pavo con zanahoria", "Fruta", "Pescado y puré de verduras"),
    ("Garbanzos con espinacas", "Bacalao al horno con tomate", "Natillas", "Tortilla francesa con calabacín"),
]


def build(path, year=2026, month=10):
    styles = getSampleStyleSheet()
    cell = styles["BodyText"]
    cell.fontSize = 7
    cell.leading = 8
    header = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES"]
    rows = [header]
    i = 0
    for week in calendar.monthcalendar(year, month):
        row = []
        for wd in range(5):
            d = week[wd]
            if not d:
                row.append("")
                continue
            if date(year, month, d) == date(year, month, 12):
                row.append(f"{d}\nFESTIVO")
                continue
            a, b, c, cena = MENUS[i % len(MENUS)]
            i += 1
            row.append(f"{d}\n{a}\n{b}\n{c}\nCena: {cena}")
        rows.append(row)
    t = Table(rows, colWidths=[150] * 5)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("FONTSIZE", (0, 0), (-1, -1), 7)]))
    doc = SimpleDocTemplate(path, pagesize=landscape(A4))
    doc.build([Paragraph(f"MENÚ COMEDOR · OCTUBRE {year} · BASAL", styles["Title"]), t])


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "sample.pdf")
