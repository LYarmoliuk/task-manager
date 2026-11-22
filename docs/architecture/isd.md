---
owner: "@LYarmoliuk"
status: published
review_date: 2027-05-20
tags: [architecture]
---
# ISD — Infrastructure Specification Document

> Проєкт: **task-manager**. Сформовано 2026-11-15. Дизайн системи — [SDD](sdd.md).

## 1. Топологія розгортання

Поточна топологія: **локальна (процес на машині розробника)**.
Команда запуску: `pip install -r requirements.txt  &&  uvicorn app.main:app --reload`

## 2. Середовища

| Середовище | Як запускається | Сховище | Конфігурація |
|---|---|---|---|
| dev | `pip install -r requirements.txt  &&  uvicorn app.main:app --reload` | — | локальний `.env` |
| test | CI-конвеєр (complexity-report, secret-scan) | тимчасове/in-memory | змінні CI |
| production | не розгорнуто (навчальний проєкт) — цільова: контейнерна | — | секрети в менеджері секретів |

## 3. Змінні середовища (без секретів)

| Змінна | Де використовується | Примітка |
|---|---|---|
| `DEPENDENCY_API_TOKEN` | `.env.example` | секрет — значення не фіксується |
| `SONAR_TOKEN` | `scripts/sonar_api.py` | секрет — значення не фіксується |
| `SONAR_URL` | `lab9_work/scripts/sonar_sqale.py` | див. `.env.example` |

Додаткова змінна: `STATS_V2_TTL` (TTL кешу `GET /api/v2/stats`, за замовчуванням 60; не секрет).

## 4. Сховища даних

- окремих сховищ не виявлено

## 5. CI/CD

### `.github/workflows/complexity-report.yml`

- Тригери: pull_request, push
- Jobs: complexity
- Стадії (steps): Checkout (повна історія для churn); Дозволити git у контейнері; Встановити CLI-сканери; Звіти складності (JSON та CSV); Churn Rate за 90 днів (Git CLI); Матриця Hotspots; Зберегти артефакт збірки
- Quality Gates: не виявлено

### `.github/workflows/secret-scan.yml`

- Тригери: pull_request, push
- Jobs: gitleaks
- Стадії (steps): —
- Quality Gates: не виявлено

## 6. Моніторинг і резервне копіювання

- Моніторинг: логи застосунку (stdout); health-ендпоінт відсутній — рекомендація
- Резервне копіювання: щоденний знімок сховища (дані застосунку) + історія коду в Git.

| Показник | Цільове значення | Статус |
|---|---|---|
| RTO (допустимий час відновлення) | 4 години | цільове, не вимірювалось |
| RPO (допустима втрата даних) | 24 години | цільове, не вимірювалось |

## 7. Відкат релізу

1. `git revert <merge-commit>` або повернення попереднього тегу/образу.
2. Повторний запуск: `pip install -r requirements.txt  &&  uvicorn app.main:app --reload`.
3. Відновлення даних зі знімка в межах RPO.

## 8. Розгортання компонентів

### checkout

Входить до процесу застосунку; запускається командою `pip install -r requirements.txt  &&  uvicorn app.main:app --reload`. Опис: [SDD](sdd.md).

### config

Входить до процесу застосунку; запускається командою `pip install -r requirements.txt  &&  uvicorn app.main:app --reload`. Опис: [SDD](sdd.md).

### dependency

Входить до процесу застосунку; запускається командою `pip install -r requirements.txt  &&  uvicorn app.main:app --reload`. Опис: [SDD](sdd.md).

### main

Входить до процесу застосунку; запускається командою `pip install -r requirements.txt  &&  uvicorn app.main:app --reload`. Опис: [SDD](sdd.md).

### models

Входить до процесу застосунку; запускається командою `pip install -r requirements.txt  &&  uvicorn app.main:app --reload`. Опис: [SDD](sdd.md).

### payments

Входить до процесу застосунку; запускається командою `pip install -r requirements.txt  &&  uvicorn app.main:app --reload`. Опис: [SDD](sdd.md).

### privacy

Входить до процесу застосунку; запускається командою `pip install -r requirements.txt  &&  uvicorn app.main:app --reload`. Опис: [SDD](sdd.md).

### reporting

Входить до процесу застосунку; запускається командою `pip install -r requirements.txt  &&  uvicorn app.main:app --reload`. Опис: [SDD](sdd.md).

### services

Входить до процесу застосунку; запускається командою `pip install -r requirements.txt  &&  uvicorn app.main:app --reload`. Опис: [SDD](sdd.md).

### validators

Входить до процесу застосунку; запускається командою `pip install -r requirements.txt  &&  uvicorn app.main:app --reload`. Опис: [SDD](sdd.md).

### lab10_stats_v2

Читає `STATS_V2_TTL`; запускається разом із застосунком: `pip install -r requirements.txt  &&  uvicorn app.main:app --reload`.

## Пов'язані документи

- [[sdd]]
- [[0003-documentation-as-code-mkdocs]]
- [[environment]]
- [[maintenance]]

**Теги:** #architecture
