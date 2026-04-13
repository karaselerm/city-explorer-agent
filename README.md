# CityExplorer Agent (PoC)

PoC агентной системы для построения прогулочных маршрутов по городу (2-4 часа) с учетом ограничений пользователя, fallback-логики и наблюдаемости.

Если хотите сразу посмотреть демо без запуска контейнеров, откройте:

- Витрина: [https://karaselerm.github.io/city-explorer-agent/demo/](https://karaselerm.github.io/city-explorer-agent/demo/)
- Интерактивная песочница: [https://karaselerm.github.io/city-explorer-agent/demo/playground.html](https://karaselerm.github.io/city-explorer-agent/demo/playground.html)

Это статические HTML-страницы на GitHub Pages, они доступны без локального запуска проекта.

## Что уже реализовано

- агентный orchestration pipeline: `retrieve -> rank -> route -> explain -> export -> memory`;
- внешний KB и tools: Overpass API + локальный fallback dataset;
- поддержка **любого города** через гео-резолвер (Nominatim) + проверка актуального названия;
- обработка исторических названий (например, `Leningrad` -> `Saint Petersburg`) с явным предупреждением;
- state/memory: SQLite-профиль и история маршрутов;
- guardrails: валидация входа, anti-injection маркеры, подтверждение side effects (`.ics`);
- observability: `logs/events.jsonl`, trace шагов, счетчики ошибок/fallback;
- web backend API + web frontend UI + docker-compose запуск;
- режимы перемещения: `walk`, `bike`, `car`, `transit` (влияют на ETA и подсказки сегментов);
- маршрут на карте + ссылки "как доехать" по каждому сегменту;
- карточки мест с фото и коротким описанием (через enrichment/fallback-data);
- CLI режим для demo/debug.

## Архитектура (коротко)

- Backend API: [web/backend/server.py](web/backend/server.py)
- Frontend UI: [web/frontend/index.html](web/frontend/index.html)
- Orchestrator: [src/city_explorer/orchestrator.py](src/city_explorer/orchestrator.py)
- System Design: [docs/system-design.md](docs/system-design.md)
- Governance: [docs/governance.md](docs/governance.md)

## Быстрый старт

### Вариант A: Docker Compose

```bash
cd city-explorer-agent
docker compose up --build
```

После старта:
- Frontend UI: `http://localhost:8010`
- Backend API health: `http://localhost:8011/api/health`

Остановка:

```bash
docker compose down
```

### Вариант B: без Docker

1. Backend + встроенная веб-страница (один процесс):

```bash
CITY_EXPLORER_PORT=8011 python3 run_api_server.py
```

2. Открыть в браузере:
- `http://localhost:8011`

## CLI demo (дополнительно)

```bash
python3 run_city_explorer.py \
  --user-id demo_user \
  --city "Leningrad" \
  --duration-hours 3 \
  --max-distance-km 6 \
  --must-category museum \
  --must-category park \
  --must-category cafe \
  --transport-mode transit \
  --budget low \
  --quiet \
  --style culture
```

## Тесты

```bash
uv run pytest
```

## Структура репозитория

```text
.
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── run_api_server.py
├── run_city_explorer.py
├── web/
│   ├── backend/server.py
│   └── frontend/
│       ├── index.html
│       ├── styles.css
│       ├── app.js
│       └── nginx.conf
├── src/city_explorer/
├── data/
├── tests/
└── docs/
```
