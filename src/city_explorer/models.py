from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class UserRequest:
    user_id: str
    city: str
    duration_hours: float = 3.0
    max_distance_km: float = 6.0
    must_categories: list[str] = field(default_factory=list)
    avoid_categories: list[str] = field(default_factory=list)
    style: str = "balanced"
    budget: str = "medium"  # low | medium | high
    quiet: bool = False
    with_plan_b: bool = True
    transport_mode: str = "walk"  # walk | bike | car | transit


@dataclass(slots=True)
class POI:
    poi_id: str
    name: str
    lat: float
    lon: float
    category: str
    tags: dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    description: str = ""
    photo_url: str = ""
    wiki_url: str = ""


@dataclass(slots=True)
class RankedPOI:
    poi: POI
    score: float
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RouteStop:
    order: int
    poi: POI
    walk_distance_km_from_prev: float
    eta_minutes_from_prev: int
    dwell_minutes: int
    distance_km_from_prev: float = 0.0
    travel_mode: str = "walk"
    travel_instruction: str = ""
    segment_map_url: str = ""


@dataclass(slots=True)
class RoutePlan:
    city: str
    total_distance_km: float
    total_duration_minutes: int
    stops: list[RouteStop] = field(default_factory=list)
    alternatives: list[POI] = field(default_factory=list)
    explanation: str = ""
    warnings: list[str] = field(default_factory=list)
    map_overview_url: str = ""
    transport_mode: str = "walk"
    city_meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    ok: bool
    data: Any = None
    error: str | None = None
    latency_ms: int = 0


@dataclass(slots=True)
class TraceEvent:
    step: str
    ok: bool
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CityResolution:
    query: str
    canonical_name: str
    country: str
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float
    center_lat: float
    center_lon: float
    warning: str = ""
    suggestions: list[str] = field(default_factory=list)
