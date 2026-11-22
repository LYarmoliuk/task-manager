# Task Manager API

A simple REST API for task management.

## Technology Stack

- Python 3.13
- FastAPI
- Pydantic
- Pytest
- Uvicorn

## Features

- Create tasks
- Get all tasks
- Get task by ID
- Update task status
- Delete tasks
- Validate task data

## Призначення

Система для керування завданнями: користувачі створюють, переглядають і відстежують задачі.

## Швидкий старт

```bash
git clone <repo-url>
cd task-manager
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Конфігурація: скопіюйте `.env.example` у `.env`. Деталі середовищ — [ISD](docs/architecture/isd.md).

## Онбординг нового розробника

1. Прочитайте розділ «Призначення» вище.
2. Запустіть систему за «Швидким стартом».
3. Вивчіть архітектуру: [SDD](docs/architecture/sdd.md); рішення — `docs/architecture/adr/`.
4. Розгортання та CI/CD: [ISD](docs/architecture/isd.md).
5. Правила супроводу: [docs/architecture/maintenance.md](docs/architecture/maintenance.md) (зміна коду = зміна документації).

## API

- `GET /api/v2/stats` — повертає статистику (версія 2). TTL кешу задається змінною `STATS_V2_TTL` (за замовчуванням 60).

## Перевірки документації (Definition of Done)

| Що перевіряється | Інструмент | Де запускається |
|---|---|---|
| Контракти API | Spectral (`spectral lint docs/api/openapi.yaml`, 0 errors) | CI `docs.yml` |
| Розмітка Markdown | markdownlint-cli2 | CI `docs.yml` |
| Посилання, nav, wikilinks | `mkdocs build --strict` | CI `docs.yml` |
| Актуальність | `review_date` у front matter, `scripts/docs_review_audit.py` | CI `docs.yml` |

Правила внеску: [CONTRIBUTING](docs/developer/CONTRIBUTING.md).
