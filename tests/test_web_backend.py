from city_explorer.models import POI, RoutePlan, RouteStop
from web.backend.server import _build_user_request, _normalize_categories, _plan_to_payload


def test_normalize_categories_supports_csv_and_list() -> None:
    assert _normalize_categories("museum, park, cafe") == ["museum", "park", "cafe"]
    assert _normalize_categories(["museum", "  park  ", ""]) == ["museum", "park"]
    assert _normalize_categories("hookah places,bars") == ["hookah", "bar"]


def test_build_user_request_has_defaults() -> None:
    req = _build_user_request({"city": "moscow"})
    assert req.city == "moscow"
    assert req.duration_hours == 3.0
    assert req.max_distance_km == 6.0
    assert req.with_plan_b is True
    assert req.transport_mode == "walk"


def test_plan_payload_contains_map_links() -> None:
    poi = POI(
        poi_id="p1",
        name="Point",
        lat=55.75,
        lon=37.61,
        category="museum",
        tags={},
        source="sample",
    )
    plan = RoutePlan(
        city="moscow",
        total_distance_km=1.2,
        total_duration_minutes=90,
        stops=[
            RouteStop(
                order=1,
                poi=poi,
                walk_distance_km_from_prev=0.3,
                eta_minutes_from_prev=4,
                dwell_minutes=20,
            )
        ],
    )

    payload = _plan_to_payload(plan)

    assert payload["city"] == "moscow"
    assert payload["stops"][0]["map_url"].startswith("https://www.openstreetmap.org/")
