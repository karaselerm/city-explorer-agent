# System Design — CityExplorer Agent (PoC)

## 1. Ключевые архитектурные решения

1. Агентная оркестрация через фиксированный execution graph:
- `safety -> memory_load -> retrieve -> rank -> route -> explain -> export -> memory_update`.

2. Разделение deterministic и agentic частей:
- агент решает порядок шагов и fallback-переходы;
- tools выполняют детерминированные операции и валидации.

3. Надежность через graceful degradation:
- live retrieval (Overpass) -> cache -> sample dataset;
- route fallback при ошибке оптимизации;
- частичный ответ вместо hard fail.

4. Наблюдаемость по умолчанию:
- structured logs (jsonl), trace шагов, счетчики ошибок/таймаутов.

## 2. Состав модулей и роли

- `CLI/API layer`: принимает запрос и возвращает артефакты.
- `Orchestrator`: управляет state-machine, retry/fallback, stop conditions.
- `Retriever`: получает POI из Overpass, нормализует и кэширует.
- `Ranker`: фильтрует/оценивает кандидатов.
- `RouteBuilder`: строит последовательность остановок и проверяет constraints.
- `Exporter`: формирует markdown/json/ics.
- `MemoryStore`: хранит профиль и историю маршрутов в SQLite.
- `SafetyGuard`: anti-injection и side-effect подтверждения.
- `EventLogger`: логи и базовые метрики reliability.

## 3. Основной workflow

1. `Input validation`: проверка запроса и guardrails.
2. `Load memory`: загрузка предпочтений пользователя.
3. `Retrieve`: запрос к Overpass.
4. `Retrieve fallback`: при ошибке/timeout -> кэш или sample dataset.
5. `Filter + rank`: удаление avoid, scoring must/preferences.
6. `Route build`: nearest-neighbor эвристика с лимитами дистанции/времени.
7. `Fallback route`: top-N порядок при ошибке route builder.
8. `Explain`: объяснение выбора и предупреждения.
9. `Persist`: запись профиля/истории, логирование trace.
10. `Export`: сохранение в `outputs/`.

Stop conditions:
- успешная сборка маршрута;
- safety validation fail;
- empty ranked list после fallback.

## 4. State / Memory / Context Handling

### Session state (in-flight)

- request_id;
- constraints (duration, distance, must/avoid);
- candidate and ranked POI lists;
- trace шагов и ошибки.

### Persistent memory

- `user_profiles`:
  - preferred categories,
  - last_city,
  - last_budget,
  - updated_at.
- `route_history`:
  - city,
  - stops summary,
  - warnings,
  - created_at.

### Context budget policy

- в runtime-контекст входят только структурированные поля;
- полные сырые ответы Overpass не сохраняются в memory;
- логи содержат технические поля, без чувствительных персональных данных.

## 5. Retrieval-контур

Источник:
- OpenStreetMap Overpass API (`POST /api/interpreter`).

Конвейер:
1. Build query по city bounds и категориям.
2. Fetch с timeout=12s.
3. Normalize к `POI` схеме.
4. Cache by `(city, categories)` с TTL 30 мин.
5. Fallback:
- cache -> local sample dataset.

Ограничения:
- максимум 100 кандидатов;
- только разрешенные категории;
- unknown city -> sample fallback.

## 6. Tool/API интеграции

### Overpass Retriever

- Input: `city`, `categories`, `limit`.
- Output: `list[POI]`.
- Errors: timeout, network, invalid json, unknown city.
- Side effects: обновление локального кэша.

### Route Builder

- Input: ranked candidates + constraints.
- Output: ordered stops + ETA + distance.
- Errors: empty candidates, unknown city.
- Side effects: нет.

### Export Tool

- Input: route plan + format.
- Output: файл в `outputs/`.
- Side effects: запись в файловую систему.
- Guardrail: `.ics` только после подтверждения.

## 7. Failure modes, fallback, guardrails

| Failure mode | Detect | Fallback |
|---|---|---|
| Overpass timeout/network fail | retriever error | cache/sample mode |
| мало кандидатов | `candidate_count < threshold` | relax constraints (default categories) |
| route build exception | caught exception | static top-3 fallback route |
| конфликт constraints | evaluator на этапе route | partial route + warning |
| injection markers | safety validation | hard reject запроса |

Guardrails:
- deny-list инъекций;
- лимит stop count;
- подтверждение side-effects;
- untrusted external data policy.

## 8. Ограничения (SLO/SLA PoC)

- `p95 e2e latency <= 30s`;
- `p95 retriever latency <= 12s`;
- `tool error rate <= 10%`;
- `fallback success rate >= 95%`;
- ресурсный бюджет: single-process локальный runtime.

## 9. Почему дизайн закрывает оба трека

Агентный:
- контроль переходов оркестратора;
- прозрачный trace шагов;
- eval-friendly структура и измеримые constraint checks.

Инфраструктурный:
- предсказуемое деградирование;
- retries/caching/timeouts;
- минимальная, но рабочая observability и risk controls.
