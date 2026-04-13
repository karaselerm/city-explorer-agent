# Data Flow Diagram

```mermaid
flowchart LR
    Req["User request"] --> Parsed["Structured request"]
    Parsed --> Safety["Safety checks"]
    Safety --> Session["Session state"]

    Session --> Retr["Retriever"]
    Retr --> Raw["Raw OSM payload"]
    Raw --> Norm["Normalized POI"]
    Norm --> Ranked["Ranked candidates"]
    Ranked --> Route["Route plan"]

    Route --> Rendered["Response payload"]
    Rendered --> Exported["Export files"]

    Session --> MemWrite["SQLite memory write"]
    Session --> Logs["events.jsonl"]
    Retr --> Logs
    Route --> Logs
    Exported --> Logs
```

## Что хранится

| Тип данных | Хранилище | TTL/Retention | Комментарий |
|---|---|---|---|
| User preferences (категории/город/бюджет) | SQLite `user_profiles` | до ручной очистки | без PII |
| Route history (сводка остановок) | SQLite `route_history` | до ручной очистки | для personalization/evals |
| Tool/trace logs | `logs/events.jsonl` | 14 дней | latency, status, errors |
| Retriever cache | `runtime/poi_cache.json` | 30 минут | ускорение + деградация |

## Что не хранится

- точная live-геолокация пользователя;
- платежные данные;
- контактные или иные чувствительные персональные данные.
