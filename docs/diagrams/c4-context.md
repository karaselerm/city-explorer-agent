# C4 Context

```mermaid
flowchart LR
    User["User / Traveler"]
    System["CityExplorer Agent PoC"]

    OSM[("OpenStreetMap Overpass API")]
    LLM[("LLM Provider (optional)")]
    Storage[("SQLite Memory")]
    Observability[("Logs + Metrics")]

    User -->|"route request"| System
    System -->|"POI query"| OSM
    System -->|"planning/explanation"| LLM
    System -->|"read/write profile and history"| Storage
    System -->|"events/traces"| Observability
```

Границы:
- пользователь взаимодействует только с CityExplorer;
- внешние API рассматриваются как недоверенные источники;
- side effects ограничены локальным экспортом и локальным storage.
