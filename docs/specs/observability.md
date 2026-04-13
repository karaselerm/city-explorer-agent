# Spec: Observability / Evals

## Логирование

Файл:
- `logs/events.jsonl`

События:
- `request_start`
- `tool_call`
- `request_end`

Поля:
- `request_id`, `ts`, `ok`, `latency_ms`, `tool`, `error`, `used_fallback`.

## Метрики (минимальный набор PoC)

- `total_requests`
- `completed_requests`
- `fallback_requests`
- `tool_errors`
- `tool_timeouts`
- `last_latency_ms`

## Eval checks

### Online checks (на каждый запрос)

1. `constraint_satisfied`
- route distance <= max distance
- route duration <= duration budget
- avoid categories absent

2. `response_non_empty`
- есть хотя бы одна остановка в итоговом плане

3. `fallback_coverage`
- если live retriever упал, есть ли деградированный результат

### Offline checks (smoke tests)

- `tests/test_smoke.py`:
  - успешная генерация маршрута;
  - корректное отклонение невалидного запроса.

## Алертинг (для расширения)

- alert при `tool_error_rate > 20%` за окно;
- alert при `p95 latency > 30s`;
- alert при `fallback_requests` резком росте.
