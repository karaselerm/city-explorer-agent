```markdown
# C4 — Component (ядро агента)

```mermaid
flowchart TB
    INPUT[User Input]

    PARSE[Intent Parser]
    PLAN[Planner]
    SELECT[Tool Selector]

    RETRIEVE[POI Retriever]
    FILTER[Filter & Rank]
    ROUTE[Route Builder]

    STATE[State Manager]
    OUTPUT[Response Builder]

    INPUT --> PARSE
    PARSE --> PLAN
    PLAN --> SELECT

    SELECT --> RETRIEVE
    RETRIEVE --> FILTER
    FILTER --> ROUTE

    ROUTE --> STATE
    STATE --> OUTPUT

Идея: LLM управляет логикой, tools делают вычисления.