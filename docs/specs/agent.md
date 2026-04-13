# Spec: Agent / Orchestrator

## Назначение

Оркестрация полного pipeline маршрута с контролем качества, безопасностью и fallback-поведением.

## Контракт

Input:
- `UserRequest { user_id, city, duration_hours, max_distance_km, must/avoid categories, style, budget, quiet }`

Output:
- `OrchestratorResult { request_id, plan?, trace[], errors[], used_fallback }`

## Execution steps

1. `safety_check`
2. `memory_load`
3. `retrieve_poi`
4. `relax_constraints` (optional)
5. `rank_filter`
6. `build_route`
7. `memory_update`

## Правила переходов

- `safety_check fail` -> terminate with error.
- `retrieve fail` -> terminate (если нет fallback данных).
- `candidate_count < threshold` -> `relax_constraints` + retry retrieval.
- `route fail` -> static top-N fallback route.

## Stop conditions

- маршрут собран;
- safety reject;
- ranked list пуст после fallback.

## Retry/Fallback

- Retriever: 1 fallback попытка с default categories.
- Routing: fallback без оптимизации (top-N order).

## Инварианты

- итоговый маршрут не превышает лимит `max_distance_km` (или обрезается);
- итоговый маршрут не превышает `duration_hours` (или обрезается);
- категории из `avoid` не попадают в результат.
