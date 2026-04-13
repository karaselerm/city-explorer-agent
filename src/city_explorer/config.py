from __future__ import annotations

from pathlib import Path

PRESET_CITY_BOUNDS: dict[str, tuple[float, float, float, float, float, float, str]] = {
    # min_lat, min_lon, max_lat, max_lon, center_lat, center_lon, country
    "moscow": (55.70, 37.48, 55.82, 37.72, 55.7558, 37.6176, "Russia"),
    "saint petersburg": (59.88, 30.20, 60.02, 30.45, 59.9311, 30.3609, "Russia"),
    "riga": (56.92, 24.00, 57.02, 24.20, 56.9496, 24.1052, "Latvia"),
}

HISTORICAL_CITY_ALIASES: dict[str, str] = {
    "ленинград": "saint petersburg",
    "ленінград": "saint petersburg",
    "leningrad": "saint petersburg",
    "свердловск": "yekaterinburg",
    "sverdlovsk": "yekaterinburg",
    "бомбей": "mumbai",
    "bombay": "mumbai",
    "calcutta": "kolkata",
    "мадрас": "chennai",
    "madras": "chennai",
    "константинополь": "istanbul",
    "constantinople": "istanbul",
}

CATEGORY_TO_OSM_FILTER: dict[str, str] = {
    "museum": "tourism=museum",
    "park": "leisure=park",
    "cafe": "amenity=cafe",
    "viewpoint": "tourism=viewpoint",
    "landmark": "historic=monument",
    "gallery": "tourism=gallery",
    "theatre": "amenity=theatre",
    "shopping": "shop=mall",
    "library": "amenity=library",
    "beach": "natural=beach",
    "bar": "amenity=bar",
    "hookah": "amenity=hookah_lounge",
}

CATEGORY_ALIASES: dict[str, str] = {
    "hookah lounge": "hookah",
    "hookah places": "hookah",
    "hookah_place": "hookah",
    "bars": "bar",
    "museums": "museum",
    "parks": "park",
    "cafes": "cafe",
    "coffee": "cafe",
    "coffee shop": "cafe",
    "coffee shops": "cafe",
}

DEFAULT_CATEGORIES = ["museum", "park", "cafe"]
POPULAR_CATEGORIES = [
    "museum",
    "park",
    "cafe",
    "viewpoint",
    "landmark",
    "gallery",
    "theatre",
    "shopping",
    "library",
    "beach",
]

TRANSPORT_SPEED_KMH: dict[str, float] = {
    "walk": 4.8,
    "bike": 15.0,
    "car": 28.0,
    "transit": 22.0,
}
TRANSPORT_LABELS: dict[str, str] = {
    "walk": "пешком",
    "bike": "на велосипеде",
    "car": "на машине",
    "transit": "на общественном транспорте",
}

TOOL_TIMEOUT_SEC = 12
RETRIEVER_MAX_CANDIDATES = 100
RETRIEVER_FALLBACK_MIN_CANDIDATES = 10
RETRIEVER_CACHE_TTL_SEC = 60 * 30

MAX_PLANNER_STEPS = 10
MAX_ROUTE_STOPS = 6

RUNTIME_DIR = Path("runtime")
LOG_DIR = Path("logs")
OUTPUT_DIR = Path("outputs")
SAMPLE_DATA_PATH = Path("data/sample_poi_moscow.json")


def ensure_dirs() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def normalize_category_name(raw: str) -> str:
    value = (raw or "").strip().lower().replace("-", " ").replace("_", " ")
    value = " ".join(value.split())
    if not value:
        return ""
    return CATEGORY_ALIASES.get(value, value)
