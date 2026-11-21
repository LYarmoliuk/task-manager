---
owner: "@LYarmoliuk"
status: published
review_date: 2027-02-19
tags: [ops]
---
# Стандарти коду

Джерело правил — конфігурації в репозиторії (ЛР№1–7); цей документ їх лише перелічує.

Виявлені конфігурації: `.pre-commit-config.yaml`, `sonar-project.properties`.

Git-хуки: `.pre-commit-config.yaml`, `hooks/deprecation.py`, `hooks/wikilinks.py`.

Принципи: тести разом з кодом (`pytest`), складність функцій за порогом, що перевіряє хук/CI; коміти — у форматі Conventional Commits (`docs(...)`, `feat(...)`, `refactor(...)`).

## Пов'язані документи

- [[CONTRIBUTING]]
- [[sdd]]

**Теги:** #ops
