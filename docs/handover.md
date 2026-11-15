# Handover Package — task-manager

Дата: 2026-11-15

## 1. Реєстр документів паспорта

| Документ | Власник | Цикл | Останній перегляд | Статус |
|---|---|---|---|---|
| README.md | LYarmoliuk | 90 дн. | 2026-11-15 | актуальний |
| docs/isd.md | LYarmoliuk | 90 дн. | 2026-11-15 | актуальний |
| docs/sdd.md | LYarmoliuk | 180 дн. | 2026-11-15 | актуальний |
| docs/architecture/adr/ | LYarmoliuk | 180 дн. | 2026-11-15 | актуальний |
| docs/maintenance.md | LYarmoliuk | 90 дн. | 2026-11-15 | актуальний |

## 2. Онбординг нового розробника

1. Прочитайте `README.md` → «Призначення».
2. Клонуйте репозиторій і відкрийте теку проєкту.
3. Налаштуйте середовище: `.env` з `.env.example` (змінні — у `docs/isd.md`).
4. Запустіть: `pip install -r requirements.txt  &&  python main.py`.
5. Вивчіть `docs/sdd.md` та ADR, перевірте `GET /api/v2/stats`.

## 3. Декларація Bus Factor

| Компонент | Авторів у Git | Головний автор | Частка | Single point of knowledge |
|---|---|---|---|---|
| checkout | 1 | LYarmoliuk | 100% | ТАК |
| config | 1 | LYarmoliuk | 100% | ТАК |
| dependency | 1 | LYarmoliuk | 100% | ТАК |
| main | 1 | LYarmoliuk | 100% | ТАК |
| models | 1 | LYarmoliuk | 100% | ТАК |
| payments | 1 | LYarmoliuk | 100% | ТАК |
| privacy | 1 | LYarmoliuk | 100% | ТАК |
| reporting | 1 | LYarmoliuk | 100% | ТАК |
| services | 1 | LYarmoliuk | 100% | ТАК |
| validators | 1 | LYarmoliuk | 100% | ТАК |

Ризик втрати знань: **ВИСОКИЙ** (10 з 10 компонентів тримає одна людина).

План усунення: парне володіння (pair review кожного PR), документування «темних зон» у SDD, ротація власників документів за `docs/maintenance.md`, перевірка онбордингу новою людиною.

## 4. Вердикт «Always Ready to Handover»

**ТАК за документацією**: аудиторії покриті, дрейфу немає, метрики в нормі. Застереження: Bus Factor = 1 у 10 компонентах, знання не розподілені.
