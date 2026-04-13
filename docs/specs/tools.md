# Spec: Tools / APIs

## 1) Overpass Retriever Tool

Purpose:
- получить кандидаты POI для заданного города и категорий.

Input:
- `city`
- `categories[]`
- `limit`

Output:
- `ToolResult(ok, data=list[POI], error, latency_ms)`

Timeout:
- 12 секунд.

Side effects:
- запись в локальный cache.

## 2) Route Builder Tool

Purpose:
- построить последовательность точек и оценку времени/дистанции.

Input:
- ranked POI
- `duration_hours`
- `max_distance_km`

Output:
- `RoutePlan(stops, total_distance_km, total_duration_minutes)`

Errors:
- unknown city;
- empty candidates.

## 3) Export Tool

Purpose:
- сохранить маршрут в файл.

Formats:
- markdown, json, ics.

Guardrails:
- `ics` требует явного подтверждения (`confirm-side-effects`).

Side effects:
- запись файлов в `outputs/`.
