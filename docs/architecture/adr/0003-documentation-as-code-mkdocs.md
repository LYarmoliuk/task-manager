---
owner: "@LYarmoliuk"
status: published
review_date: 2027-05-20
tags: [architecture]
adr_status: Accepted
---
# ADR-0003: Documentation as Code на MkDocs Material

- Статус: **accepted**
- Дата: 2026-11-21

## Контекст

Документація (SDD, ISD, ADR, API) жила в окремих файлах без автоматичної перевірки та публікації.

## Розглянуті альтернативи

- Docusaurus
- Sphinx
- GitHub Wiki

## Рішення

Обрано **MkDocs Material** + GitHub Actions + GitHub Pages. Обґрунтування: версіонування через Git, обов'язкове рев'ю, автоматична збірка і публікація без ручних кроків.

## Наслідки

- (+) документація проходить рев'ю й strict-збірку як код
- (−) потрібна підтримка Python-залежностей і CI-конвеєра
- Пов'язано: [[isd]], [[CONTRIBUTING]]; зміна рішення — новий ADR, цей отримає статус superseded.

## Пов'язані документи

- [[isd]]
- [[CONTRIBUTING]]

**Теги:** #architecture
