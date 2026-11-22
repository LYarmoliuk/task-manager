---
owner: "@LYarmoliuk"
status: published
review_date: 2027-02-19
tags: [ops]
---
# Правила внеску (CONTRIBUTING)

1. Створіть гілку від `main` і зробіть зміну малими комітами (Conventional Commits).
2. Запустіть тести та перевірки документації локально (див. [середовище](environment.md)).
3. Відкрийте Pull Request; зміни в `docs/` потребують рев'ю власника (див. `.github/CODEOWNERS`).
4. Дотримуйтесь стандартів із [стандартів коду](standards.md).

## Пов'язані документи

- [[environment]]
- [[standards]]
- [[isd]]

**Теги:** #ops

## Definition of Done: docs-or-don't-merge

Pull request, що змінює **публічну поведінку** (новий ендпоінт, зміну конфігурації, формат відповіді), не зливається,
доки не виконано:

- [ ] Оновлено сторінки в `docs/` (і `review_date` у front matter).
- [ ] Оновлено контракт `docs/api/openapi.yaml` (версія за SemVer).
- [ ] Додано запис у `CHANGELOG.md`.
- [ ] Локально проходять `markdownlint`, `spectral lint` і `mkdocs build --strict`.
- [ ] Рев'ю власника документа (`.github/CODEOWNERS`).

Застарілі сторінки не видаляються: їм ставлять `status: deprecated` і `superseded_by` у front matter.
Для мажорних змін документації ставиться тег `docs-vX.Y` — знімок відновлюється з тегу, як код релізу.
