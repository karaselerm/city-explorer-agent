# C4 Container

```mermaid
flowchart TB
    User["User"] --> CLI["CLI / API"]

    CLI --> ORCH["Orchestrator"]
    ORCH --> SAFE["Safety Guard"]
    ORCH --> RET["POI Retriever"]
    ORCH --> RANK["Ranker"]
    ORCH --> ROUTE["Route Builder"]
    ORCH --> EXP["Exporter"]
    ORCH --> MEM["Memory Store"]
    ORCH --> OBS["Event Logger"]

    RET --> OSM[("Overpass API")]
    RET --> CACHE[("Retriever Cache")]
    RET --> SAMPLE[("Local Sample Data")]

    MEM --> SQLITE[("SQLite runtime/memory.db")]
    OBS --> LOGS[("logs/events.jsonl")]
    EXP --> OUT[("outputs/*.md,json,ics")]
```

Контейнерные решения:
- Orchestrator как точка координации;
- Retriever имеет multi-source режим (live/cache/sample);
- Observability и Memory вынесены в отдельные контейнеры для стабильности и тестируемости.
