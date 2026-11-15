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
python main.py
```

Конфігурація: скопіюйте `.env.example` у `.env`. Деталі середовищ — [ISD](docs/isd.md).

## Онбординг нового розробника

1. Прочитайте розділ «Призначення» вище.
2. Запустіть систему за «Швидким стартом».
3. Вивчіть архітектуру: [SDD](docs/sdd.md); рішення — `docs/architecture/adr/`.
4. Розгортання та CI/CD: [ISD](docs/isd.md).
5. Правила супроводу: [docs/maintenance.md](docs/maintenance.md) (зміна коду = зміна документації).
