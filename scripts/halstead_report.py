"""Звіт за метриками Холстеда для проєкту (два рушії).

  --engine radon   (за замовчуванням) офіційний CLI-сканер radon: оператори = арифметика,
                   порівняння, and/or/not, +=; виклики, ключові слова та роздільники НЕ рахуються.
  --engine tokens  класичне лексичне визначення із завдання: оператори = ключові слова,
                   знаки операцій і роздільники; операнди = імена, числа, рядки.
                   Реалізовано на стандартному модулі tokenize (без залежностей).

Використання (з кореня проєкту, з активованим .venv):
    python scripts/halstead_report.py app
    python scripts/halstead_report.py app --engine tokens
    python scripts/halstead_report.py app --files app/privacy/services.py app/dependency.py app/validators.py
    python scripts/halstead_report.py app --functions app/privacy/services.py --engine tokens

Формули:  eta=eta1+eta2;  N=N1+N2;  V=N*log2(eta);  D=(eta1/2)*(N2/eta2);  E=V*D
"""
import argparse
import ast
import io
import keyword
import math
import sys
import token
import tokenize
from pathlib import Path

from radon.metrics import h_visit

SKIP = {token.NEWLINE, token.NL, token.INDENT, token.DEDENT, token.ENDMARKER,
        token.COMMENT, token.ENCODING}
FSTRING_MID = {getattr(token, n) for n in ("FSTRING_MIDDLE", "FSTRING_END") if hasattr(token, n)}
FSTRING_START = getattr(token, "FSTRING_START", None)


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")  # ігноруємо BOM (лаб. 5)


def loc(source: str) -> int:
    return sum(1 for ln in source.splitlines() if ln.strip() and not ln.strip().startswith("#"))


def derive(h1, h2, n1, n2) -> dict:
    eta, n = h1 + h2, n1 + n2
    v = n * math.log2(eta) if eta > 1 else 0.0
    d = (h1 / 2) * (n2 / h2) if h2 else 0.0
    return {"h1": h1, "h2": h2, "N1": n1, "N2": n2, "eta": eta, "N": n, "V": v, "D": d, "E": v * d}


def token_counts(source: str, first=None, last=None) -> dict:
    ops, opd = {}, {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type in SKIP or tok.type in FSTRING_MID:
            continue
        if first and not (first <= tok.start[0] <= last):
            continue
        if tok.type == token.OP or (tok.type == token.NAME and keyword.iskeyword(tok.string)):
            ops[tok.string] = ops.get(tok.string, 0) + 1
        elif tok.type in (token.NAME, token.NUMBER, token.STRING) or tok.type == FSTRING_START:
            key = "f\"\"" if tok.type == FSTRING_START else tok.string
            opd[key] = opd.get(key, 0) + 1
    return derive(len(ops), len(opd), sum(ops.values()), sum(opd.values()))


def measure(source: str, engine: str) -> dict:
    if engine == "tokens":
        return token_counts(source)
    t = h_visit(source).total
    return derive(t.h1, t.h2, t.N1, t.N2)


def function_measures(source: str, engine: str):
    if engine == "radon":
        for name, r in h_visit(source).functions:
            yield name, derive(r.h1, r.h2, r.N1, r.N2)
        return
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node.name, token_counts(source, node.lineno, node.end_lineno)


def row(name, m, loc_val=None):
    tail = f" {loc_val} |" if loc_val is not None else ""
    return (f"| {name} | {m['h1']} | {m['h2']} | {m['N1']} | {m['N2']} | {m['eta']} | {m['N']} "
            f"| {m['V']:.1f} | {m['D']:.2f} | {m['E']:.0f} |{tail}")


def header(first="Файл", with_loc=False):
    cols = f"| {first} | η1 | η2 | N1 | N2 | η | N | V (біт) | D | E |" + (" LOC |" if with_loc else "")
    sep = "|---" * (11 if with_loc else 10) + "|"
    return cols + "\n" + sep


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--engine", choices=["radon", "tokens"], default="radon")
    ap.add_argument("--files", nargs="*")
    ap.add_argument("--functions")
    a = ap.parse_args()

    files = sorted(p for p in Path(a.root).rglob("*.py")
                   if ".venv" not in p.parts and "__pycache__" not in p.parts)
    sources = {p: read_source(p) for p in files}

    merged = "\n".join(sources.values())
    try:
        g, how = measure(merged, a.engine), "об'єднаний словник"
    except (SyntaxError, tokenize.TokenError):
        per = [measure(s, a.engine) for s in sources.values()]
        g = derive(sum(x["h1"] for x in per), sum(x["h2"] for x in per),
                   sum(x["N1"] for x in per), sum(x["N2"] for x in per))
        how = "сума по файлах"
    print(f"## Глобальна лінія Холстеда [{a.engine}] ({len(files)} файлів, {how})\n")
    print(header("Проєкт"))
    print(row("УСЬОГО", g))
    print(f"\nLOC (непорожні, без коментарів): {sum(loc(s) for s in sources.values())}\n")

    ranked = sorted(((p, measure(s, a.engine), loc(s)) for p, s in sources.items() if s.strip()),
                    key=lambda r: r[1]["E"], reverse=True)
    print(f"## Модулі за E від більшого до меншого [{a.engine}]\n")
    print(header(with_loc=True))
    for p, m, l in ranked:
        print(row(p.as_posix(), m, l))

    if a.files:
        print(f"\n## Матриця: файли-представники [{a.engine}]\n")
        print(header(with_loc=True))
        for f in a.files:
            s = read_source(Path(f))
            print(row(Path(f).as_posix(), measure(s, a.engine), loc(s)))

    if a.functions:
        print(f"\n## Функції у {Path(a.functions).as_posix()} [{a.engine}]\n")
        print(header("Функція"))
        for name, m in function_measures(read_source(Path(a.functions)), a.engine):
            print(row(name, m))
    return 0


if __name__ == "__main__":
    sys.exit(main())
