# Data Flow

```mermaid
flowchart LR
    User --> Agent

    Agent --> Retriever
    Retriever --> RawData[Raw OSM Data]

    RawData --> Normalized
    Normalized --> Filtered
    Filtered --> Route

    Route --> Output

    Output --> Logs
    Output --> Memory
```

Что хранится
| Данные      | Где           |
| ----------- | ------------- |
| POI         | временно      |
| preferences | memory        |
| logs        | observability |


Что НЕ хранится
* точная геолокация
* PII
