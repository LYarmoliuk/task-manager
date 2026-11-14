"""Матриця зв'язності класів (Coupling Matrix) і граф залежностей у вигляді одного HTML-файлу.

Рядок = клас-споживач, стовпець = клас, на який він посилається. Клас з найбільшою кількістю
вихідних зв'язків (кандидат у God Object) підсвічується і ставиться в центр графа.

Приклад:
    python scripts/coupling_matrix.py app --scope app/checkout --out reports/coupling_baseline.html
"""
import argparse
import html
import math
import sys
from pathlib import Path

import ck_metrics

STYLE = """
body{font-family:Segoe UI,Arial,sans-serif;margin:20px;background:#fff;color:#1b1f23}
h1{font-size:20px} table{border-collapse:collapse;font-size:12px}
th,td{border:1px solid #c8ccd0;padding:3px 6px;text-align:center;white-space:nowrap}
th.row{text-align:left;background:#f3f4f6} td.hit{background:#e5484d;color:#fff;font-weight:700}
td.diag{background:#e8eaed} tr.god th.row{background:#ffd6d8;font-weight:700}
.note{margin:10px 0;font-size:13px} svg{border:1px solid #c8ccd0;margin-top:14px}
"""


def select_classes(data, prefixes):
    rows = ck_metrics.select(data["classes"], None, prefixes)
    names = {row["class"] for row in rows}
    edges = {row["class"]: [d for d in row["depends_on"] if d in names] for row in rows}
    return rows, edges


def order_names(edges):
    return sorted(edges, key=lambda name: (-len(edges[name]), name))


def matrix_html(names, edges):
    head = "".join(f"<th>{html.escape(n)}</th>" for n in names)
    lines = [f"<table><tr><th></th>{head}<th>вихідних</th></tr>"]
    for index, row in enumerate(names):
        cells = []
        for col in names:
            if row == col:
                cells.append('<td class="diag"></td>')
            else:
                hit = col in edges[row]
                cells.append('<td class="hit">1</td>' if hit else "<td></td>")
        css = ' class="god"' if index == 0 and len(edges[row]) > 8 else ""
        lines.append(f'<tr{css}><th class="row">{html.escape(row)}</th>{"".join(cells)}'
                     f"<td><b>{len(edges[row])}</b></td></tr>")
    return "\n".join(lines) + "</table>"


def layout(names):
    centre, radius, width = names[0], 260.0, 860
    others = names[1:]
    points = {centre: (width / 2, width / 2)}
    for i, name in enumerate(others):
        angle = 2 * math.pi * i / max(1, len(others))
        points[name] = (width / 2 + radius * math.cos(angle), width / 2 + radius * math.sin(angle))
    return points, width


def svg_graph(names, edges):
    points, width = layout(names)
    parts = [f'<svg width="{width}" height="{width}" xmlns="http://www.w3.org/2000/svg">']
    for src, targets in edges.items():
        for dst in targets:
            (x1, y1), (x2, y2) = points[src], points[dst]
            parts.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
                         'stroke="#9aa1a9" stroke-width="1"/>')
    for name, (x, y) in points.items():
        fill = "#e5484d" if name == names[0] and len(edges[name]) > 8 else "#3b82f6"
        parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="7" fill="{fill}"/>')
        parts.append(f'<text x="{x + 9:.0f}" y="{y + 4:.0f}" font-size="11">{html.escape(name)}</text>')
    return "\n".join(parts) + "</svg>"


def page(title, names, edges):
    total = sum(len(v) for v in edges.values())
    top = names[0]
    note = (f"Класів: {len(names)}, зв'язків: {total}. Найбільше вихідних зв'язків: "
            f"<b>{html.escape(top)}</b> ({len(edges[top])}).")
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title>"
            f"<style>{STYLE}</style></head><body><h1>{html.escape(title)}</h1>"
            f"<div class='note'>{note}</div>{matrix_html(names, edges)}{svg_graph(names, edges)}</body></html>")


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--scope", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="Coupling Matrix")
    return ap.parse_args()


def main():
    args = parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    data = ck_metrics.analyse(args.root)
    rows, edges = select_classes(data, args.scope)
    names = order_names(edges)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(page(args.title, names, edges), encoding="utf-8")
    print(f"Матрицю збережено: {args.out}  (класів {len(names)}, найбільший вихідний зв'язок: "
          f"{names[0]} = {len(edges[names[0]])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
