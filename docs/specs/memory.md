# Spec: Memory / Context

## Session state

Хранится в runtime в пределах одного запроса:
- request_id;
- constraints;
- candidate/ranked/stops;
- trace и warnings.

## Persistent memory (SQLite)

Таблицы:

1. `user_profiles`
- `user_id` (PK)
- `preferences_json`
- `updated_at`

2. `route_history`
- `id` (PK)
- `user_id`
- `city`
- `route_json`
- `created_at`

## Memory policy

- без хранения PII;
- no precise live location;
- хранение только структурированных полей;
- ручная очистка runtime допустима для PoC.

## Context budget

В оркестратор подаются:
- агрегированные preferences;
- текущие constraints;
- shortlist кандидатов.

Сырые payload внешних API в long-term memory не пишутся.
