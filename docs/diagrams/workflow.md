# Workflow

```mermaid
flowchart TD
    A[User Query] --> B[Parse Intent]

    B --> C[Retrieve POI]
    C -->|timeout| C2[Retry smaller query]

    C --> D[Filter POI]
    D -->|empty| D2[Relax constraints]

    D --> E[Build Route]
    E -->|fail| E2[Heuristic route]

    E --> F[Generate Response]
    F --> G[Output]

Важно: система всегда возвращает результат (даже degraded).