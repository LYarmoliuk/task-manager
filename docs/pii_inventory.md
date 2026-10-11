# PII inventory (підготовчий етап)

Система: Task Manager API (FastAPI, Python 3.13), сховище: in-memory `PrivacyStore`
(dataclass-сутності), автентифікація: Bearer-токен -> (user_id, role), ролі `user` / `admin`.

## Категорії даних

| Категорія | Поля | Джерело | Сховище | Пов'язані сутності | У логах | В експорті |
|---|---|---|---|---|---|---|
| Прямі ідентифікатори | full_name, email, external_id | реєстрація | `users` | settings, activity, orders, consents | email маскується, ім'я в логи не пишеться | так |
| Контактні дані | phone, address | профіль | `users` | orders (billing_*) | phone маскується (`***67`) | так |
| Технічні ідентифікатори | ip_address, user_agent | HTTP-запити | `activity` | users | не логуються | так |
| Історія дій | action, occurred_at, meta | події застосунку | `activity` | users | лише тип операції й correlation ID | так |
| Транзакційні записи | amount, currency, status, billing_name, billing_address | оформлення замовлення | `orders` | users | не логуються | так |
| Дані про згоду | purpose, status, policy_version, source, timestamps | GRANT/REVOKE | `consents` | users | лише purpose і safe-ref суб'єкта | так |
| Налаштування | language, timezone, theme | профіль | `settings` | users | не логуються | так |

## Ніколи не повертаються через Data Export

`password_hash`, `reset_token`, `is_flagged_fraud` (antifraud), токени сесій / секрети інтеграцій,
`audit` (внутрішній журнал), дані інших користувачів. Перелік відображено в `meta.excluded_fields` експорту.

## Політика логування

| Рівень | Поля | Дія |
|---|---|---|
| Дозволено | correlation_id, тип операції, level, logger, timestamp, safe-ref суб'єкта (`ref_xxxxxxxx`), результат | пишемо як є |
| Маскується | email (`a***@example.com`), phone (`***67`) | часткове маскування |
| Заборонено | password, password_hash, access/refresh/reset token, api_key, session secret, Authorization/Cookie, Bearer-значення | повна заміна на `[REDACTED]` |

## Політика Erasure

| Сутність | Дія | Обґрунтування |
|---|---|---|
| users | ANONYMIZE | email -> `deleted-<id>@anon.local` (унікальний, не відновлюється), решта PII очищається |
| settings | DELETE | не потрібні |
| activity | ANONYMIZE | лишається дія/час; ip, user_agent, meta очищаються |
| orders | RETAIN | retention (облік): лишаються сума/валюта/статус/дата; billing_name/address видаляються |
| consents | RETAIN | доказ згоди без PII; активні згоди відкликаються |
| audit | RETAIN | privacy-safe: без значень PII |
| auth_tokens | DELETE | анулюються |

## Контрольні тестові дані (синтетичні)

Alice: `alice@example.com`, `+380501234567`, `Alice Tester`, `Kyiv, Test St 1`, `EXT-ALICE-001`,
`pbkdf2$ALICE_HASH_DO_NOT_EXPORT`, `RESET-ALICE-TOKEN`, ip `203.0.113.10`. Bob і Admin: дані інших суб'єктів / ролі.
