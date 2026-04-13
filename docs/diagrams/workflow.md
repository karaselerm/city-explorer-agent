# Workflow / Execution Graph

```mermaid
flowchart TD
    A["Receive request"] --> B["Safety validation"]
    B -->|fail| B1["Reject with reason"]
    B -->|pass| C["Load user memory"]

    C --> D["Retrieve POI (Overpass)"]
    D -->|timeout/error| D1["Fallback: cache/sample"]
    D1 --> E["Filter + Rank"]
    D -->|success| E

    E -->|0 candidates| E1["Relax filters + retry retrieval"]
    E1 --> E2["If still empty -> fail with message"]
    E -->|candidates>0| F["Build route"]

    F -->|exception| F1["Fallback route: static top-N"]
    F -->|ok| G["Compose explanation"]
    F1 --> G

    G --> H["Persist memory + append history"]
    H --> I["Export artifacts"]
    I --> J["Return response + trace"]
```

Гарантия PoC:
- система стремится вернуть полезный результат даже при деградации внешних зависимостей;
- hard fail происходит только при нарушении safety или полном отсутствии данных после fallback.
