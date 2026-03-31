# Agent / Orchestrator

## Шаги

1. parse_intent
2. retrieve_poi
3. filter
4. build_route
5. generate_response

## Stop conditions

- маршрут построен
- max steps

## Retry

- retriever → retry
- routing → fallback

## Инварианты

- маршрут <= заданной дистанции
- категории соблюдены