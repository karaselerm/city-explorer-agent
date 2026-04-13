from __future__ import annotations

import urllib.parse
from dataclasses import dataclass

from .config import MAX_ROUTE_STOPS, TRANSPORT_LABELS, TRANSPORT_SPEED_KMH
from .geo import haversine_km
from .models import CityResolution, RankedPOI, RoutePlan, RouteStop, UserRequest

DWELL_MINUTES = {
    "museum": 55,
    "park": 35,
    "cafe": 25,
    "viewpoint": 15,
    "landmark": 20,
    "gallery": 40,
    "theatre": 60,
    "shopping": 35,
    "library": 30,
    "beach": 45,
}


@dataclass(slots=True)
class RouteBuilder:
    def build(self, req: UserRequest, ranked: list[RankedPOI], city: CityResolution) -> RoutePlan:
        if not ranked:
            raise ValueError("empty candidate list")

        mode = self._normalize_mode(req.transport_mode)
        speed = TRANSPORT_SPEED_KMH[mode]

        remaining = [r.poi for r in ranked]
        current_lat = city.center_lat
        current_lon = city.center_lon

        route_stops: list[RouteStop] = []
        total_distance_km = 0.0
        total_minutes = 0
        stop_index = 1

        effective_max_distance = req.max_distance_km
        theoretical_max = req.duration_hours * speed
        warnings: list[str] = []
        if req.max_distance_km > theoretical_max * 1.25:
            effective_max_distance = round(theoretical_max * 1.25, 2)
            warnings.append(
                f"Лимит {req.max_distance_km} км не соотносится с режимом '{TRANSPORT_LABELS[mode]}'. "
                f"Использую рабочий лимит {effective_max_distance} км."
            )

        while remaining and stop_index <= MAX_ROUTE_STOPS:
            nearest = min(
                remaining,
                key=lambda p: haversine_km(current_lat, current_lon, p.lat, p.lon),
            )
            step_dist = haversine_km(current_lat, current_lon, nearest.lat, nearest.lon)
            step_minutes = max(1, int((step_dist / speed) * 60))
            dwell = DWELL_MINUTES.get(nearest.category, 20)

            projected_distance = total_distance_km + step_dist
            projected_minutes = total_minutes + step_minutes + dwell

            if projected_distance > effective_max_distance:
                break
            if projected_minutes > int(req.duration_hours * 60):
                break

            route_stops.append(
                RouteStop(
                    order=stop_index,
                    poi=nearest,
                    walk_distance_km_from_prev=round(step_dist, 2),
                    distance_km_from_prev=round(step_dist, 2),
                    eta_minutes_from_prev=step_minutes,
                    dwell_minutes=dwell,
                    travel_mode=mode,
                    travel_instruction=self._travel_instruction(mode, step_dist, step_minutes),
                    segment_map_url=self._segment_map_url(mode, current_lat, current_lon, nearest.lat, nearest.lon),
                )
            )

            total_distance_km = projected_distance
            total_minutes = projected_minutes
            current_lat, current_lon = nearest.lat, nearest.lon
            remaining = [p for p in remaining if p.poi_id != nearest.poi_id]
            stop_index += 1

        if not route_stops:
            first = ranked[0].poi
            route_stops.append(
                RouteStop(
                    order=1,
                    poi=first,
                    walk_distance_km_from_prev=0.0,
                    distance_km_from_prev=0.0,
                    eta_minutes_from_prev=0,
                    dwell_minutes=DWELL_MINUTES.get(first.category, 20),
                    travel_mode=mode,
                    travel_instruction="Начальная точка маршрута",
                    segment_map_url=self._segment_map_url(mode, city.center_lat, city.center_lon, first.lat, first.lon),
                )
            )
            total_minutes = route_stops[0].dwell_minutes

        overview_url = self._overview_url(mode, route_stops)

        return RoutePlan(
            city=city.canonical_name,
            total_distance_km=round(total_distance_km, 2),
            total_duration_minutes=total_minutes,
            stops=route_stops,
            warnings=warnings,
            map_overview_url=overview_url,
            transport_mode=mode,
            city_meta={
                "query": city.query,
                "country": city.country,
                "canonical_name": city.canonical_name,
                "suggestions": city.suggestions,
            },
        )

    def _normalize_mode(self, mode: str) -> str:
        mode = (mode or "walk").strip().lower()
        if mode not in TRANSPORT_SPEED_KMH:
            return "walk"
        return mode

    def _travel_instruction(self, mode: str, distance_km: float, eta_min: int) -> str:
        if mode == "walk":
            return f"Идите пешком {distance_km:.2f} км (~{eta_min} мин)."
        if mode == "bike":
            return f"Езжайте на велосипеде {distance_km:.2f} км (~{eta_min} мин)."
        if mode == "car":
            return f"Езжайте на машине {distance_km:.2f} км (~{eta_min} мин)."

        if distance_km < 1.2:
            return f"Короткий участок: пешком до остановки и далее транспортом (~{eta_min} мин)."
        if distance_km < 4:
            return f"Оптимально автобус/трамвай (~{eta_min} мин)."
        return f"Оптимально метро/электричка + пешком (~{eta_min} мин)."

    def _segment_map_url(self, mode: str, lat1: float, lon1: float, lat2: float, lon2: float) -> str:
        if mode == "transit":
            params = urllib.parse.urlencode(
                {
                    "api": 1,
                    "origin": f"{lat1},{lon1}",
                    "destination": f"{lat2},{lon2}",
                    "travelmode": "transit",
                }
            )
            return f"https://www.google.com/maps/dir/?{params}"

        engine_map = {
            "walk": "fossgis_osrm_foot",
            "bike": "fossgis_osrm_bike",
            "car": "fossgis_osrm_car",
        }
        engine = engine_map.get(mode, "fossgis_osrm_foot")
        route = urllib.parse.quote(f"{lat1},{lon1};{lat2},{lon2}", safe="")
        return f"https://www.openstreetmap.org/directions?engine={engine}&route={route}"

    def _overview_url(self, mode: str, stops: list[RouteStop]) -> str:
        if not stops:
            return ""
        if len(stops) == 1:
            p = stops[0].poi
            return f"https://www.openstreetmap.org/?mlat={p.lat}&mlon={p.lon}#map=16/{p.lat}/{p.lon}"

        waypoints = [f"{s.poi.lat},{s.poi.lon}" for s in stops]
        params = {
            "api": 1,
            "origin": waypoints[0],
            "destination": waypoints[-1],
            "travelmode": "transit" if mode == "transit" else ("driving" if mode == "car" else ("bicycling" if mode == "bike" else "walking")),
        }
        if len(waypoints) > 2:
            params["waypoints"] = "|".join(waypoints[1:-1])
        return f"https://www.google.com/maps/dir/?{urllib.parse.urlencode(params)}"
