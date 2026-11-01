"""Інформаційна складність за Чепіним: класифікація змінних P / M / C / T.

Cch = 1*P + 2*M + 3*C + 0.5*T

Правила (пріоритет C -> M -> P -> T):
  C  змінна стоїть в умові if / while / тернарному виразі / assert / фільтрі генератора;
  M  змінна перезаписується (>= 2 присвоювань, +=, присвоювання параметру) або мутується
     (obj[k] = v, obj.attr = v, .append/.update/...);
  P  змінна лише читається (параметр, константа з конфігурації, одноразово створена локальна);
  T  змінна використовується тільки як прямий аргумент виклику іншої функції (прокидається далі).
У методів поля self.<ім'я> рахуються як змінні. Імена функцій, класів і вбудованих
викликів не змінні. Константи (ІМЕНА_З_ВЕЛИКИХ_ЛІТЕР) читаються як конфігурація (P).

Використання:
    python scripts/chapin_report.py app/payments.py --function charge_order
    python scripts/chapin_report.py app/payments.py --all
    python scripts/chapin_report.py app/payments.py --function charge_order --expect 16
"""
import argparse
import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

WEIGHTS = {"P": 1.0, "M": 2.0, "C": 3.0, "T": 0.5}
MUTATORS = frozenset({"append", "extend", "insert", "pop", "remove", "clear", "update",
                      "setdefault", "add", "discard", "sort", "reverse", "popitem"})
SELF_NAMES = ("self", "cls")
CONST_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
RISK_LIMIT = 10


def set_parents(tree):
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child._parent = parent


def var_key(node):
    """Ім'я змінної для Name або self.<поле>; для іншого вузла None."""
    if isinstance(node, ast.Name) and node.id not in SELF_NAMES:
        return node.id
    is_self_attr = (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                    and node.value.id in SELF_NAMES)
    return f"self.{node.attr}" if is_self_attr else None


def in_condition(node):
    child, parent = node, getattr(node, "_parent", None)
    while parent is not None and not isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if isinstance(parent, (ast.If, ast.While, ast.IfExp, ast.Assert)) and parent.test is child:
            return True
        if isinstance(parent, ast.comprehension) and child in parent.ifs:
            return True
        child, parent = parent, getattr(parent, "_parent", None)
    return False


def is_call_func(node):
    parent = getattr(node, "_parent", None)
    return isinstance(parent, ast.Call) and parent.func is node


def is_direct_arg(node):
    parent = getattr(node, "_parent", None)
    if not isinstance(parent, ast.Call) or parent.func is node:
        return False
    return node in parent.args or any(kw.value is node for kw in parent.keywords)


def mutation_root(node):
    """True, якщо вузол є коренем запису obj[k] = v / obj.a = v / obj.append(...)."""
    child, parent = node, getattr(node, "_parent", None)
    while isinstance(parent, (ast.Subscript, ast.Attribute)) and parent.value is child:
        if isinstance(parent.ctx, (ast.Store, ast.Del)):
            return True
        grand = getattr(parent, "_parent", None)
        if (isinstance(parent, ast.Attribute) and parent.attr in MUTATORS
                and isinstance(grand, ast.Call) and grand.func is parent):
            return True
        child, parent = parent, grand
    return False


class Usage:
    def __init__(self):
        self.stores = 0
        self.augmented = False
        self.mutated = False
        self.cond = False
        self.arg_loads = 0
        self.other_loads = 0

    def add_store(self, node):
        self.stores += 1
        self.augmented = self.augmented or isinstance(getattr(node, "_parent", None), ast.AugAssign)

    def add_load(self, node):
        if mutation_root(node):
            self.mutated = True
        if in_condition(node):
            self.cond = True
        if is_direct_arg(node):
            self.arg_loads += 1
        else:
            self.other_loads += 1


def collect_usage(fn):
    usage = defaultdict(Usage)
    for node in ast.walk(fn):
        key = var_key(node)
        if key is None or is_call_func(node):
            continue
        if isinstance(node, ast.Attribute) and isinstance(node._parent, ast.Attribute) and node._parent.value is node:
            pass
        if isinstance(node.ctx, ast.Store):
            usage[key].add_store(node)
        else:
            usage[key].add_load(node)
    return usage


def param_names(fn):
    args = fn.args
    names = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]
    names += [a.arg for a in (args.vararg, args.kwarg) if a]
    return [n for n in names if n not in SELF_NAMES]


def is_modified(use, is_param):
    reassigned = use.stores >= (1 if is_param else 2)
    return reassigned or use.augmented or use.mutated


def classify(name, use, is_param):
    if use.cond:
        return "C", "використовується в умові"
    if is_modified(use, is_param):
        return "M", "перезаписується або мутується"
    if use.arg_loads and not use.other_loads:
        return "T", "лише прокидається аргументом у виклик"
    return "P", "лише читається"


def is_variable(name, use, params):
    if name in params or name.startswith("self."):
        return True
    if use.stores:
        return True
    return bool(CONST_RE.match(name)) and (use.arg_loads + use.other_loads) > 0


def analyze(fn):
    usage = collect_usage(fn)
    params = set(param_names(fn))
    rows = []
    for name in list(param_names(fn)) + sorted(k for k in usage if k not in params):
        use = usage.get(name)
        if use is None or not is_variable(name, use, params):
            continue
        cls, why = classify(name, use, name in params)
        rows.append((name, "параметр" if name in params else "локальна/поле", cls, why))
    return rows


def totals(rows):
    count = {"P": 0, "M": 0, "C": 0, "T": 0}
    for _, _, cls, _ in rows:
        count[cls] += 1
    cch = sum(WEIGHTS[k] * v for k, v in count.items())
    return count, cch


def iter_functions(tree):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node.name, node
        if isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield f"{node.name}.{sub.name}", sub


def fmt(value):
    return f"{value:g}".replace(".", ",")


def print_function(name, fn):
    rows = analyze(fn)
    count, cch = totals(rows)
    print(f"### {name}\n")
    print("| Змінна | Походження | Клас | Вага | Обґрунтування |\n| --- | --- | --- | --- | --- |")
    for var, origin, cls, why in rows:
        print(f"| `{var}` | {origin} | {cls} | {fmt(WEIGHTS[cls])} | {why} |")
    print(f"\nP={count['P']}, M={count['M']}, C={count['C']}, T={count['T']}")
    print(f"Cch = 1·{count['P']} + 2·{count['M']} + 3·{count['C']} + 0,5·{count['T']} = {fmt(cch)}")
    verdict = "ВИСОКИЙ РИЗИК (Cch > 10)" if cch > RISK_LIMIT else "в межах норми (Cch <= 10)"
    print(f"Рівень: {verdict}\n")
    return cch


def print_summary(items):
    print("| Функція | P | M | C | T | Cch |\n| --- | --- | --- | --- | --- | --- |")
    total = 0.0
    for name, fn in items:
        count, cch = totals(analyze(fn))
        total += cch
        print(f"| {name} | {count['P']} | {count['M']} | {count['C']} | {count['T']} | {fmt(cch)} |")
    print(f"\nСума Cch по модулю: {fmt(total)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--function", help="ім'я функції або Клас.метод")
    ap.add_argument("--all", action="store_true", help="короткий підсумок по всіх функціях")
    ap.add_argument("--expect", type=float, help="очікуваний Cch; інакше код виходу 1")
    args = ap.parse_args()

    tree = ast.parse(Path(args.file).read_text(encoding="utf-8-sig"))
    set_parents(tree)
    items = list(iter_functions(tree))
    if args.all or not args.function:
        print_summary(items)
        return 0
    chosen = [(n, f) for n, f in items if n == args.function or n.endswith("." + args.function)]
    if not chosen:
        print(f"Функцію {args.function} не знайдено", file=sys.stderr)
        return 2
    cch = print_function(*chosen[0])
    if args.expect is not None and cch != args.expect:
        print(f"ОЧІКУВАЛОСЬ Cch={fmt(args.expect)}, отримано {fmt(cch)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
