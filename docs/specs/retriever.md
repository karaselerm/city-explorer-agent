# Spec: Retriever

## Источники

Primary:
- Overpass API (`https://overpass-api.de/api/interpreter`)

Fallback:
- `runtime/poi_cache.json` (TTL 30 минут)
- `data/sample_poi_moscow.json`

## Input

- `city: str`
- `categories: list[str]`
- `limit: int <= 100`

## Output

- `ToolResult { ok, data=list[POI], error?, latency_ms }`

POI schema:
- `poi_id, name, lat, lon, category, tags, source`

## Нормализация

- `tags -> category` mapping:
  - `tourism=museum -> museum`
  - `leisure=park -> park`
  - `amenity=cafe -> cafe`
  - `tourism=viewpoint -> viewpoint`
  - `historic=monument -> landmark`

## Ограничения

- timeout: 12 секунд;
- максимум 100 POI;
- поддерживаемые bounds: `moscow`, `saint petersburg`, `riga`.

## Ошибки

- network/timeout;
- invalid json;
- unknown city;
- no data after fallback.
