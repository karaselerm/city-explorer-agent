from city_explorer.models import UserRequest
from city_explorer.orchestrator import CityExplorerOrchestrator


def test_reconcile_must_and_avoid_categories() -> None:
    orchestrator = CityExplorerOrchestrator()
    req = UserRequest(
        user_id="u1",
        city="Moscow",
        must_categories=["museum", "park", "Museum"],
        avoid_categories=["park", "bar", "museum"],
    )

    overlap = orchestrator._normalize_and_reconcile_categories(req)

    assert overlap == ["museum", "park"]
    assert req.must_categories == ["museum", "park"]
    assert req.avoid_categories == ["bar"]
