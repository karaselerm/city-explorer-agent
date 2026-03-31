# Governance — CityExplorer Agent

## 1. Risk Register

| Риск | Вероятность | Влияние | Защита |
|------|------------|--------|--------|
| Утечка геолокации | M | H | не хранить координаты |
| Prompt injection | L | M | untrusted input |
| API overload | M | M | rate limit |

---

## 2. Политика данных

- не хранить PII
- не хранить координаты пользователя
- хранить только агрегированные данные

---

## 3. Guardrails

- подтверждение действий (export)
- ограничение tool calls
- LLM не принимает решения напрямую

---

## 4. Fail-safe

- fallback при ошибках API
- частичный ответ
