# Deployment Playbook (Luxury Max)

Этот документ нужен, чтобы быстро получить публичный URL для асинхронной проверки проекта.

## 1) Самый быстрый путь: локально + tunnel

1. Поднять систему:

```bash
docker compose up --build -d
```

2. Проверить локально:
- `http://localhost:8010` (UI)
- `http://localhost:8011/api/health` (API)

3. Пробросить публичный URL:

```bash
cloudflared tunnel --url http://localhost:8010
```

или

```bash
ngrok http 8010
```

4. Передать URL ментору.

## 2) Постоянный деплой: один сервис (backend + UI)

Backend уже отдает статические файлы `web/frontend`, поэтому можно деплоить только `Dockerfile.backend`.

### Render / Railway / Fly

- Build source: репозиторий GitHub
- Dockerfile: `Dockerfile.backend`
- Port: `8000`
- Health check: `/api/health`

После деплоя:
- UI: `https://<your-domain>/`
- API: `https://<your-domain>/api/health`

## 3) Отдельный frontend сервис (опционально)

Если нужен отдельный frontend контейнер:
- Backend: `Dockerfile.backend`
- Frontend: `Dockerfile.frontend`
- Во frontend должен быть reverse proxy `/api -> backend`.

## 4) Smoke checklist перед отправкой URL

- открывается главная страница;
- строится маршрут по базовому сценарию;
- есть trace шагов;
- при `Export ICS` без подтверждения возвращается ошибка;
- при подтверждении `.ics` экспорт проходит;
- в `logs/events.jsonl` видны `request_start/tool_call/request_end`.
