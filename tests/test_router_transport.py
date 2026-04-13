from city_explorer.models import CityResolution, POI, RankedPOI, UserRequest
from city_explorer.router import RouteBuilder


def test_router_applies_transport_mode_and_instructions() -> None:
    city = CityResolution(
        query="Moscow",
        canonical_name="Moscow",
        country="Russia",
        min_lat=55.70,
        min_lon=37.48,
        max_lat=55.82,
        max_lon=37.72,
        center_lat=55.7558,
        center_lon=37.6176,
    )
    poi = POI(
        poi_id="p1",
        name="Point",
        lat=55.76,
        lon=37.62,
        category="museum",
        tags={},
        source="sample",
    )
    req = UserRequest(user_id="u", city="Moscow", transport_mode="car", duration_hours=2, max_distance_km=10)

    plan = RouteBuilder().build(req, [RankedPOI(poi=poi, score=1.0)], city)

    assert plan.transport_mode == "car"
    assert plan.stops[0].travel_mode == "car"
    assert "машине" in plan.stops[0].travel_instruction.lower()
