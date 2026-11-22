#!/usr/bin/env python3
"""Безперервний аудит актуальності документації (ЛР№11, Завдання 3).

Читає front matter усіх docs/**/*.md, порівнює review_date з поточною датою, виводить прострочені
та deprecated сторінки. Відсутність owner/status/review_date = помилка (exit 1); прострочені - попередження.
"""
import argparse
import datetime as dt
import pathlib
import re
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--as-of", help="YYYY-MM-DD (симуляція дати)")
ap.add_argument("--strict-overdue", action="store_true", help="прострочені сторінки = помилка")
a = ap.parse_args()
today = dt.date.fromisoformat(a.as_of) if a.as_of else dt.date.today()
FM = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.S)
STATUSES = {"draft", "in-review", "published", "deprecated"}
rows, missing, deprecated = [], [], []
for p in sorted(pathlib.Path("docs").rglob("*.md")):
    m = FM.match(p.read_text(encoding="utf-8"))
    meta = {}
    if m:
        for ln in m.group(1).splitlines():
            k, _, v = ln.partition(":")
            meta[k.strip()] = v.strip().strip('"')
    miss = [k for k in ("owner", "status", "review_date") if not meta.get(k)]
    if miss or meta.get("status") not in STATUSES:
        missing.append((str(p), miss or ["status?"]))
        continue
    if meta["status"] == "deprecated":
        deprecated.append((str(p), meta.get("superseded_by", "-")))
        continue
    rd = dt.date.fromisoformat(meta["review_date"])
    if rd < today:
        rows.append((str(p), meta["owner"], meta["status"], meta["review_date"], (today - rd).days))
print("Аудит актуальності станом на %s" % today)
print("Прострочені review_date: %d" % len(rows))
for r in rows:
    print("  - %s  owner=%s status=%s review_date=%s (прострочено на %d дн.)" % r)
print("Deprecated: %d" % len(deprecated))
for d, s in deprecated:
    print("  - %s -> %s" % d if False else "  - %s -> %s" % (d, s))
print("Без паспорта/з помилкою: %d" % len(missing))
for f, m in missing:
    print("  ! %s: %s" % (f, ", ".join(m)))
sys.exit(1 if missing or (rows and a.strict_overdue) else 0)
