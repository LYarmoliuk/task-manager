"""Об'єктні метрики Python-проєкту: CK (WMC, CBO, LCOM, RFC, DIT, NOC), Лоренц-Кід (PIM, NMO) і MOOD.

Навіщо: SonarQube Community не віддає coupling_between_objects, lcom4, DIT і MOOD для Python,
тому ці числа рахує AST-аналіз. Вихідний JSON має поле measures у форматі відповіді Sonar Web API.

Визначення (скрізь «клас» = клас верхнього рівня з каталогу, що скануємо):
  WMC   сума цикломатичної складності методів (radon)
  CBO   кількість ІНШИХ проєктних класів, на які клас посилається у тілі (ефферентне зачеплення)
  LCOM4 кількість компонентів зв'язності методів: методи пов'язані, якщо читають/пишуть спільне self.<поле>
  LCOM* нормований LCOM Хендерсона-Селлерса, 0 = ідеальна згуртованість, 1 = повна відсутність
  RFC   методи класу + різні викликані зовнішні імена (наближено)
  DIT   глибина успадкування: клас без батька = 1, зовнішній батько (Exception) = 1 рівень
  NOC   кількість прямих нащадків
  PIM   розмір публічного інтерфейсу (власні + успадковані публічні методи)
  NMO   перевизначені методи (є у проєктному предка)
  MHF/AHF  частка прихованих (_name) методів / атрибутів; COF  частка зв'язаних пар класів

Приклад:
    python scripts/ck_metrics.py app --out reports/ck.json --files app/services.py
    python scripts/ck_metrics.py app --scope app/checkout --limit-cbo 8 --limit-lcom 0.2
"""
import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

from radon.complexity import cc_visit
from radon.visitors import Class

NEUTRAL_BASES = frozenset({"object", "Protocol", "ABC", "Generic"})
SKIP_DIRS = frozenset({"__pycache__", ".venv", "venv", "tests"})


def is_dunder(name):
    return name.startswith("__") and name.endswith("__")


def node_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def base_name(node):
    if isinstance(node, ast.Subscript):
        return base_name(node.value)
    return node_name(node)


def self_attrs(func):
    """Множини self.<поле>: усі звернення і лише присвоєння."""
    used, stored = set(), set()
    for node in ast.walk(func):
        is_self = isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self"
        if is_self:
            used.add(node.attr)
            if isinstance(node.ctx, ast.Store):
                stored.add(node.attr)
    return used, stored


def level_names(stmt):
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        return {stmt.target.id}
    if isinstance(stmt, ast.Assign):
        return {t.id for t in stmt.targets if isinstance(t, ast.Name)}
    return set()


class ClassInfo:
    def __init__(self, node, path):
        self.node = node
        self.name = node.name
        self.file = path
        bases = (base_name(b) for b in node.bases)
        self.bases = [b for b in bases if b and b not in NEUTRAL_BASES]
        funcs = (ast.FunctionDef, ast.AsyncFunctionDef)
        self.methods = {m.name: m for m in node.body if isinstance(m, funcs)}
        self.attributes = self._collect_attributes()
        self.wmc = 0

    def _collect_attributes(self):
        names = set()
        for method in self.methods.values():
            names |= self_attrs(method)[1]
        for stmt in self.node.body:
            names |= level_names(stmt)
        return names - set(self.methods)


def class_wmc(source):
    return {b.name: sum(m.complexity for m in b.methods) for b in cc_visit(source) if isinstance(b, Class)}


def iter_py_files(root):
    for path in sorted(Path(root).rglob("*.py")):
        if not SKIP_DIRS.intersection(path.parts):
            yield path


def register(classes, info):
    """Клас з уже зайнятим іменем зберігається під ключем «Ім'я@файл», а не затирає попередній."""
    key = info.name
    if key in classes:
        print(f"УВАГА: дублікат імені класу {key}: {classes[key].file} і {info.file}", file=sys.stderr)
        key = f"{key}@{info.file}"
    classes[key] = info


def load_classes(root):
    classes = {}
    for path in iter_py_files(root):
        source = path.read_text(encoding="utf-8-sig")
        wmc = class_wmc(source)
        for node in ast.parse(source).body:
            if isinstance(node, ast.ClassDef):
                info = ClassInfo(node, path.as_posix())
                info.wmc = wmc.get(node.name, 0)
                register(classes, info)
    return classes


def referenced_classes(info, known):
    found = set()
    for stmt in info.node.body:
        for node in ast.walk(stmt):
            name = node_name(node)
            if name in known and name != info.name:
                found.add(name)
    return found


def called_names(info):
    names = set()
    for node in ast.walk(info.node):
        if isinstance(node, ast.Call) and node_name(node.func):
            names.add(node_name(node.func))
    return names - set(info.methods)


def find_root(parent, item):
    while parent[item] != item:
        parent[item] = parent[parent[item]]
        item = parent[item]
    return item


def count_components(foots):
    parent = {name: name for name in foots}
    owner = {}
    for name, attrs in foots.items():
        for attr in attrs:
            other = owner.setdefault(attr, name)
            parent[find_root(parent, name)] = find_root(parent, other)
    return len({find_root(parent, name) for name in parent})


def lcom_hs(foots, attrs):
    count, total_attrs = len(foots), len(attrs)
    if count <= 1 or total_attrs == 0:
        return 0.0
    hits = sum(len(f) for f in foots.values())
    return round(max(0.0, (count - hits / total_attrs) / (count - 1)), 3)


def cohesion(info):
    foots = {}
    for name, method in info.methods.items():
        if not is_dunder(name):
            foots[name] = self_attrs(method)[0] & info.attributes
    return count_components(foots), lcom_hs(foots, info.attributes)


def depth(name, classes, cache):
    if name not in classes:
        return 1
    if name not in cache:
        cache[name] = 1
        parents = [depth(b, classes, cache) for b in classes[name].bases]
        cache[name] = 1 + max(parents) if parents else 1
    return cache[name]


def ancestors(info, classes):
    seen, queue = set(), list(info.bases)
    while queue:
        name = queue.pop()
        if name in classes and name not in seen:
            seen.add(name)
            queue.extend(classes[name].bases)
    return seen


def inherited_methods(info, classes):
    names = set()
    for anc in ancestors(info, classes):
        names |= {n for n in classes[anc].methods if not is_dunder(n)}
    return names


def public_only(names):
    return {n for n in names if not n.startswith("_")}


def lorenz_kidd(info, classes, dit):
    inherited = inherited_methods(info, classes)
    own = [n for n in info.methods if not is_dunder(n)]
    nmo = sum(1 for n in own if n in inherited)
    six = round(nmo * dit / len(own), 2) if own else 0.0
    return {"pim": len(public_only(set(own) | inherited)), "pim_own": len(public_only(own)),
            "nmo": nmo, "nma": len(own) - nmo, "six": six,
            "overridden": sorted(n for n in own if n in inherited)}


def class_row(info, classes, edges, cache):
    dit = depth(info.name, classes, cache)
    lcom4, hs = cohesion(info)
    row = {"file": info.file, "class": info.name, "wmc": info.wmc, "cbo": len(edges[info.name]),
           "lcom4": lcom4, "lcom_hs": hs, "rfc": len(info.methods) + len(called_names(info)),
           "dit": dit, "noc": sum(1 for c in classes.values() if info.name in c.bases),
           "nom": len([n for n in info.methods if not is_dunder(n)])}
    row.update(lorenz_kidd(info, classes, dit))
    row["depends_on"] = sorted(edges[info.name])
    return row


def percent(part, whole):
    return round(100.0 * part / whole, 1) if whole else 0.0


def mood(classes, edges):
    methods = hidden_m = attrs = hidden_a = 0
    for info in classes.values():
        names = [n for n in info.methods if not is_dunder(n)]
        methods += len(names)
        hidden_m += sum(1 for n in names if n.startswith("_"))
        attrs += len(info.attributes)
        hidden_a += sum(1 for n in info.attributes if n.startswith("_"))
    count = len(classes)
    pairs = sum(len(v) for v in edges.values())
    cof = round(100.0 * pairs / (count * (count - 1)), 2) if count > 1 else 0.0
    return {"classes": count, "MHF_percent": percent(hidden_m, methods), "AHF_percent": percent(hidden_a, attrs),
            "COF_percent": cof, "coupled_pairs": pairs}


def file_measures(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["file"]].append(row)
    result = []
    for path, items in grouped.items():
        values = {"class_complexity": sum(r["wmc"] for r in items),
                  "coupling_between_objects": max(r["cbo"] for r in items),
                  "lcom4": max(r["lcom4"] for r in items),
                  "lcom_hs": max(r["lcom_hs"] for r in items)}
        measures = [{"metric": k, "value": str(v)} for k, v in values.items()]
        result.append({"component": {"key": path, "measures": measures}, "classes": [r["class"] for r in items]})
    return result


def analyse(root):
    classes = load_classes(root)
    known = set(classes)
    edges = {name: referenced_classes(info, known) for name, info in classes.items()}
    cache = {}
    rows = [class_row(info, classes, edges, cache) for info in classes.values()]
    rows.sort(key=lambda r: (r["file"], r["class"]))
    return {"root": str(root), "classes": rows, "files": file_measures(rows), "mood": {**mood(classes, edges), "root": str(root)}}


def norm_path(path):
    return path.replace("\\", "/").strip("/")


def matches(row, wanted, prefixes):
    if not wanted and not prefixes:
        return True
    return row["file"] in wanted or any(row["file"].startswith(p) for p in prefixes)


def select(rows, files, scope):
    wanted = [norm_path(f) for f in files or []]
    prefixes = [norm_path(s) for s in scope or []]
    return [row for row in rows if matches(row, wanted, prefixes)]


COLUMNS = (("Файл", "file"), ("Клас", "class"), ("WMC", "wmc"), ("CBO", "cbo"), ("LCOM4", "lcom4"),
           ("LCOM*", "lcom_hs"), ("RFC", "rfc"), ("DIT", "dit"), ("NOC", "noc"),
           ("PIM", "pim"), ("NMO", "nmo"))


def render_table(rows):
    lines = ["| " + " | ".join(title for title, _ in COLUMNS) + " |",
             "| " + " | ".join("---" for _ in COLUMNS) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row[key]) for _, key in COLUMNS) + " |")
    return "\n".join(lines)


def render_mood(data):
    return (f"MOOD (весь каталог {data['root']}, класів: {data['classes']}): MHF = {data['MHF_percent']} %, "
            f"AHF = {data['AHF_percent']} %, COF = {data['COF_percent']} % "
            f"({data['coupled_pairs']} зв'язаних пар)")


def violations(rows, limit_cbo, limit_lcom):
    bad = []
    for row in rows:
        if limit_cbo is not None and row["cbo"] > limit_cbo:
            bad.append(f"{row['class']}: CBO {row['cbo']} > {limit_cbo}")
        if limit_lcom is not None and row["lcom_hs"] > limit_lcom:
            bad.append(f"{row['class']}: LCOM* {row['lcom_hs']} > {limit_lcom}")
    return bad


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="каталог з кодом, наприклад app")
    ap.add_argument("--out", help="JSON-файл з повним результатом")
    ap.add_argument("--files", nargs="*", help="показати лише ці файли")
    ap.add_argument("--scope", nargs="*", help="показати файли за префіксом шляху")
    ap.add_argument("--limit-cbo", type=int)
    ap.add_argument("--limit-lcom", type=float)
    return ap.parse_args()


def main():
    args = parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    data = analyse(args.root)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = select(data["classes"], args.files, args.scope)
    print(render_table(rows))
    print()
    print(render_mood(data["mood"]))
    bad = violations(rows, args.limit_cbo, args.limit_lcom)
    for line in bad:
        print("ПОРУШЕННЯ ЛІМІТУ:", line)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
