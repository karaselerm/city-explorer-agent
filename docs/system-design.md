# System Design — CityExplorer Agent (PoC)

## 1. Ключевые архитектурные решения

- Агентная оркестрация (LLM + вызовы инструментов)
- Pipeline с приоритетом retrieval (OSM → фильтрация → маршрут → ответ)
- Stateless execution + лёгкая персистентная память (SQLite / JSON)
- Чёткое разделение ответственности:
  - LLM → логика, планирование, объяснение
  - Tools → детерминированные вычисления
- Fail-fast + fallback стратегия (частичный маршрут при ошибках)
---

## 2. Основные модули

### 1. Orchestrator Agent
- принимает запрос
- нормализует intent
- планирует шаги (planner)
- вызывает tools
- собирает финальный ответ

### 2. POI Retriever (Overpass)
- получает POI по bbox / area
- нормализует данные

### 3. Ranker / Filter
- фильтрация по категориям и ограничениям
- ранжирование (rule-based + optional LLM)

### 4. Route Builder
- строит порядок точек
- проверяет ограничения (distance/time)

### 5. Renderer
- формирует ответ
- добавляет объяснение
- экспорт

### 6. Memory Layer
- user preferences
- session state

### 7. Observability
- логи
- метрики
- ошибки

---

## 3. Workflow выполнения

1. User → запрос
2. Agent → parse intent
3. Retriever → fetch POI
4. Filter → shortlist
5. Route builder → ordered route
6. Agent → explanation
7. Renderer → output

---

## 4. State / Memory

### Session state
- цель маршрута
- ограничения (время, дистанция)
- выбранные POI

### Persistent memory
- предпочтения пользователя
- избранные места

### Memory policy
- без хранения PII
- TTL для логов: 7–14 дней

---

## 5. Retrieval-контур

Источник:
- OpenStreetMap (Overpass API)

Pipeline:
1. Query → bbox / area
2. Fetch → raw OSM
3. Normalize → schema
4. Filter → by tags
5. Rank → heuristic

Ограничения:
- max 100 POI
- timeout 25s

---

## 6. Tools / API интеграции

### Overpass API
- input: bbox / query
- output: POI list

### Routing (optional)
- input: coordinates
- output: distance / ETA

### Export tool
- JSON / Markdown / ICS

---

## 7. Failure modes + fallback

| Ошибка | Действие |
|------|--------|
| Overpass timeout | retry → fallback smaller query |
| нет POI | ослабить фильтры |
| routing fail | heuristic ordering |
| слишком длинный маршрут | обрезать |

---

## 8. Guardrails

- все внешние данные = untrusted
- LLM не вызывает tools напрямую
- лимит шагов агента
- подтверждение для side effects

---

## 9. Ограничения

### Latency
- target: < 20–30s
- fallback: < 10s

### Cost
- минимальный (PoC)
- ограничение токенов

### Reliability
- Устойчивая деградация: при ошибках система возвращает частичный результат