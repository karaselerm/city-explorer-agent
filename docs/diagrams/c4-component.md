# C4 Component — Orchestrator Core

```mermaid
flowchart TB
    Input["Validated User Request"] --> Safety["Safety Guard"]
    Safety --> Planner["Planner / Step Controller"]

    Planner --> MemLoad["Memory Loader"]
    Planner --> Retrieve["Retriever Adapter"]
    Retrieve --> RetryDecision{"Enough POI?"}
    RetryDecision -- "No" --> Relax["Relax Constraints"]
    Relax --> Retrieve
    RetryDecision -- "Yes" --> Rank["Filter + Rank"]

    Rank --> Route["Route Builder"]
    Route --> RouteFallback{"route ok?"}
    RouteFallback -- "No" --> Static["Static Top-N Fallback"]
    RouteFallback -- "Yes" --> Explain["Explanation Composer"]
    Static --> Explain

    Explain --> Persist["Memory Persistor"]
    Persist --> Export["Exporter"]
    Export --> Done["Final Response"]

    Planner --> Trace["Trace Collector"]
    Retrieve --> Trace
    Rank --> Trace
    Route --> Trace
    Export --> Trace
```

Роль компонентов:
- `Planner` управляет переходами и stop conditions;
- `Trace Collector` фиксирует шаги для eval/debug;
- `Relax Constraints` и `Static Top-N` реализуют graceful degradation.
