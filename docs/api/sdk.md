---
owner: "@LYarmoliuk"
status: published
review_date: 2027-02-19
tags: [api]
---
# Клієнтський SDK

SDK генерується з контракту, а не пишеться вручну:

```powershell
npx @openapitools/openapi-generator-cli generate -i docs/api/openapi.yaml -g python -o sdk/client
```

Потрібна Java 11+ (або Docker-образ `openapitools/openapi-generator-cli`). Каталог `sdk/` у Git не комітиться — він
відтворюється командою вище з [контракту](openapi.md).

## Пов'язані документи

- [[api/index]]
- [[environment]]

**Теги:** #api
