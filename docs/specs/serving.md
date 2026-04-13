# Spec: Serving / Config

## Runtime

- Язык: Python 3.11+
- Режим: локальный single-process PoC
- Entry point: `python3 run_city_explorer.py`
- Web entry point: `python3 run_api_server.py`

## Конфигурация

Основные параметры запроса:
- `--city`
- `--duration-hours`
- `--max-distance-km`
- `--must-category` / `--avoid-category`
- `--budget`, `--style`, `--quiet`

Параметры side effects:
- `--export-format`
- `--confirm-side-effects` (обязательно для `ics`)

Web API:
- `GET /api/health`
- `POST /api/plan`
- `GET /api/logs?lines=30`

Runtime env:
- `CITY_EXPLORER_HOST` (default `0.0.0.0`)
- `CITY_EXPLORER_PORT` (default `8000`)

## Версии и зависимости

- Внешние зависимости Python: не требуются (stdlib-only реализация PoC).
- Build/packaging: `pyproject.toml` (setuptools).

## Секреты

- В текущем PoC секреты не используются.
- При подключении внешнего LLM/API ключи должны идти через env vars, не в коде.

## Операционные ограничения

- сеть может быть недоступна -> обязательная поддержка fallback режимов;
- artifacts пишутся локально в `outputs/`;
- runtime state хранится в `runtime/`.

## Docker

- `Dockerfile.backend`: backend + встроенный static frontend;
- `Dockerfile.frontend`: отдельный nginx frontend (для compose);
- `docker-compose.yml`: запуск `backend` + `frontend`.
