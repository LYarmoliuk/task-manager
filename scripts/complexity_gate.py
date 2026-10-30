"""Воротар цикломатичної складності для pre-commit.

pre-commit передає у аргументах лише staged-файли (types: [python]).
Якщо хоч одна функція має CC > MAX_CC, друкуємо червоне попередження
і завершуємось з кодом 1: Git скасовує коміт.

Ручний запуск:  python scripts/complexity_gate.py app/privacy/retention.py
"""
import argparse
import os
import sys
from pathlib import Path

from radon.complexity import cc_visit

MAX_CC = 10
RED, BOLD, RESET = "\033[91m", "\033[1m", "\033[0m"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--max", type=int, default=MAX_CC, help="допустима CC (за замовчуванням 10)")
    args = ap.parse_args()

    os.system("")  # вмикає ANSI-кольори в Windows-терміналі
    # pre-commit перенаправляє stdout у канал, де Windows використовує cp1251/cp866 і кирилиця ламається
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    violations = []
    for name in args.files:
        path = Path(name)
        if path.suffix != ".py" or not path.exists():
            continue
        try:
            blocks = cc_visit(path.read_text(encoding="utf-8-sig"))
        except SyntaxError as exc:  # помилка інструмента = FAIL (правило лаб. 5)
            print(f"{RED}{BOLD}[complexity-gate] не вдалося розібрати {name}: {exc}{RESET}")
            return 1
        for b in blocks:
            if b.complexity > args.max:
                violations.append((name, b.lineno, b.name, b.complexity))

    if violations:
        print(f"{RED}{BOLD}КОМІТ ЗАБЛОКОВАНО: цикломатична складність перевищує ліміт CC>{args.max}{RESET}")
        for name, line, func, cc in sorted(violations, key=lambda v: -v[3]):
            print(f"{RED}  {name}:{line}  {func}()  CC={cc}  (ліміт {args.max}){RESET}")
        print(f"{RED}Спростіть функцію (таблиця пошуку / Extract Method) і повторіть git add + git commit.{RESET}")
        return 1

    print(f"[complexity-gate] OK: усі функції у staged-файлах мають CC<={args.max}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
