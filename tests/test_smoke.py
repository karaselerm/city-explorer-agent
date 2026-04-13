from city_explorer.models import UserRequest
from city_explorer.orchestrator import CityExplorerOrchestrator


def test_orchestrator_builds_plan_with_fallback_data() -> None:
    orchestrator = CityExplorerOrchestrator()
    req = UserRequest(
        user_id="u1",
        city="moscow",
        duration_hours=3,
        max_distance_km=6,
        must_categories=["museum", "park", "cafe"],
        style="balanced",
        budget="medium",
        quiet=True,
    )

    result = orchestrator.run(req)

    assert result.plan is not None
    assert len(result.plan.stops) >= 1
    assert result.plan.total_duration_minutes > 0


def test_orchestrator_rejects_invalid_request() -> None:
    orchestrator = CityExplorerOrchestrator()
    req = UserRequest(user_id="u2", city="moscow", duration_hours=0, max_distance_km=3)

    result = orchestrator.run(req)

    assert result.plan is None
    assert result.errors
