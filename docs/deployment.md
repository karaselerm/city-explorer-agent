# Deployment Playbook

Этот документ нужен, чтобы быстро получить публичный URL для асинхронной проверки проекта.

## 1) Самый быстрый путь: локально + tunnel

1. Поднять систему:

```bash
docker compose up --build -d
```

2. Проверить локально:
- `http://localhost:8010` (UI)
- `http://localhost:8011/api/health` (API)


4. Передать URL ментору.

## 2) Постоянный деплой: один сервис (backend + UI)

Backend уже отдает статические файлы `web/frontend`, поэтому можно деплоить только `Dockerfile.backend`.
