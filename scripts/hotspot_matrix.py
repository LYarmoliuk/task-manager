"""Синергетична матриця Hotspots: складність коду (radon) x мінливість у Git (churn).

Вхід: JSON radon (`radon cc -j`, `radon hal -j`) і історія Git за N днів.
Вихід: таблиця Markdown у консоль, файли hotspots.md і hotspots.json.

Категорії:
  CC > 10 і churn >= порога   Hotspot (High Risk)
  CC > 10 і churn <  порога   Sleeping Danger
  CC <= 10 і churn >= порога  Active Development
  CC <= 10 і churn <  порога  Stable Code

Приклад:
    radon cc app -j > reports/radon-cc.json
    radon hal app -j > reports/radon-hal.json
    python scripts/hotspot_matrix.py --cc reports/radon-cc.json --hal reports/radon-hal.json
"""
import argparse
import json
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path

HOTSPOT, SLEEPING, ACTIVE, STABLE = (
    "Hotspot (High Risk)", "Sleeping Danger", "Active Development", "Stable Code")


def read_json(path):
    raw = Path(path).read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):  # PowerShell 5 пише UTF-16
        return json.loads(raw.decode("utf-16"))
    return json.loads(raw.decode("utf-8-sig"))


def norm(path):
    return str(path).replace("\\", "/")


def max_cc_per_file(cc_data):
    result = {}
    for path, blocks in cc_data.items():
        best = ("-", 0)
        for block in iter_blocks(blocks):
            if block["complexity"] > best[1]:
                best = (block["name"], block["complexity"])
        result[norm(path)] = best
    return result


def iter_blocks(blocks):
    if not isinstance(blocks, list):
        return
    for block in blocks:
        if "complexity" in block:
            yield block
        yield from iter_blocks(block.get("methods"))
        yield from iter_blocks(block.get("closures"))


def effort_per_file(hal_data):
    return {norm(path): round(item["total"]["effort"], 1) for path, item in hal_data.items()}


def add_files_without_functions(cc_map, effort_map):
    """Файли без функцій (config.py, models.py) radon cc не повертає: беремо їх з Halstead."""
    for path in effort_map:
        if not path.endswith("__init__.py"):
            cc_map.setdefault(path, ("-", 0))
    return cc_map


def git_churn(since, rev):
    cmd = ["git", "log", rev, f"--since={since}", "--format=format:", "--name-only"]
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return Counter(norm(line.strip()) for line in out.splitlines() if line.strip())


def categorize(cc, commits, cc_limit, churn_limit):
    if cc > cc_limit:
        return HOTSPOT if commits >= churn_limit else SLEEPING
    return ACTIVE if commits >= churn_limit else STABLE


def resolve_threshold(value, commits):
    if value != "median":
        return int(value)
    return max(2, int(statistics.median(commits))) if commits else 2


def build_rows(cc_map, effort_map, churn, cc_limit, churn_arg):
    limit = resolve_threshold(churn_arg, [churn.get(path, 0) for path in cc_map])
    rows = []
    for path, (func, cc) in cc_map.items():
        commits = churn.get(path, 0)
        rows.append({"file": path, "max_cc": cc, "max_cc_function": func,
                     "effort": effort_map.get(path, 0), "commits": commits,
                     "category": categorize(cc, commits, cc_limit, limit)})
    rows.sort(key=lambda r: (r["max_cc"], r["commits"]), reverse=True)
    return rows, limit


def render_markdown(rows, cc_limit, churn_limit, since):
    lines = [f"Пороги: CC > {cc_limit} (складність), коміти >= {churn_limit} за період «{since}» (мінливість).", "",
             "| Файл | Макс. CC (функція) | Effort (Halstead) | Коміти | Категорія |",
             "| --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r['file']} | {r['max_cc']} ({r['max_cc_function']}) | {r['effort']:g} "
                     f"| {r['commits']} | {r['category']} |")
    return "\n".join(lines) + "\n"


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cc", required=True, help="JSON від radon cc -j")
    ap.add_argument("--hal", required=True, help="JSON від radon hal -j")
    ap.add_argument("--since", default="90 days ago")
    ap.add_argument("--rev", default="HEAD")
    ap.add_argument("--cc-threshold", type=int, default=10)
    ap.add_argument("--churn-threshold", default="median", help="число або median")
    ap.add_argument("--out-dir", default="reports")
    return ap.parse_args()


def main():
    args = parse_args()
    effort_map = effort_per_file(read_json(args.hal))
    cc_map = add_files_without_functions(max_cc_per_file(read_json(args.cc)), effort_map)
    churn = git_churn(args.since, args.rev)
    rows, limit = build_rows(cc_map, effort_map, churn, args.cc_threshold, args.churn_threshold)
    text = render_markdown(rows, args.cc_threshold, limit, args.since)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "hotspots.md").write_text(text, encoding="utf-8")
    (out / "hotspots.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
