from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .city_resolver import CityResolver
from .config import (
    CATEGORY_TO_OSM_FILTER,
    RETRIEVER_CACHE_TTL_SEC,
    RETRIEVER_MAX_CANDIDATES,
    SAMPLE_DATA_PATH,
    TOOL_TIMEOUT_SEC,
    normalize_category_name,
)
from .models import CityResolution, POI, ToolResult

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_ENDPOINTS = [
    OVERPASS_URL,
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]


@dataclass(slots=True)
class POIRetriever:
    cache_path: Path = field(default_factory=lambda: Path("runtime") / "poi_cache.json")
    city_resolver: CityResolver = field(default_factory=CityResolver)

    def __post_init__(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

    def fetch(
        self,
        city: str,
        categories: list[str],
        city_resolution: CityResolution | None = None,
        limit: int = RETRIEVER_MAX_CANDIDATES,
    ) -> ToolResult:
        started = time.perf_counter()
        categories = [normalize_category_name(c) for c in categories if c.strip()]
        categories = [c for c in categories if c in CATEGORY_TO_OSM_FILTER]
        if not categories:
            categories = ["museum", "park", "cafe"]

        resolved = city_resolution
        if resolved is None:
            city_res = self.city_resolver.resolve(city)
            if not city_res.ok:
                return ToolResult(
                    ok=False,
                    error=city_res.error or "failed to resolve city",
                    data=city_res.data,
                    latency_ms=self._elapsed_ms(started),
                )
            resolved = city_res.data

        cache_key = self._cache_key(resolved, categories)
        cached = self._load_from_cache(cache_key)
        if cached:
            return ToolResult(ok=True, data=cached, latency_ms=self._elapsed_ms(started))

        live = self._fetch_live_overpass(resolved, categories, limit)
        if live.ok and live.data:
            self._save_to_cache(cache_key, live.data)
            return ToolResult(ok=True, data=live.data, latency_ms=self._elapsed_ms(started))

        sample = self._fetch_sample(resolved, categories, limit)
        if sample:
            return ToolResult(
                ok=True,
                data=sample,
                error=live.error,
                latency_ms=self._elapsed_ms(started),
            )

        synthetic = self._build_synthetic_fallback(resolved, categories, limit)
        if synthetic:
            reason = live.error or "live retriever unavailable"
            return ToolResult(
                ok=True,
                data=synthetic,
                error=f"{reason}; using synthetic fallback",
                latency_ms=self._elapsed_ms(started),
            )

        return ToolResult(
            ok=False,
            error=live.error or "retriever returned no data",
            latency_ms=self._elapsed_ms(started),
        )

    def _fetch_live_overpass(self, city: CityResolution, categories: list[str], limit: int) -> ToolResult:
        started = time.perf_counter()
        query = self._build_query(city.min_lat, city.min_lon, city.max_lat, city.max_lon, categories, out_limit=max(120, limit * 4))
        primary = self._run_overpass_query(query, categories, limit)
        if primary.ok and primary.data:
            primary.latency_ms = self._elapsed_ms(started)
            return primary

        # Degradation path: fetch categories independently to reduce query size.
        if len(categories) <= 1:
            primary.latency_ms = self._elapsed_ms(started)
            return primary

        merged: list[POI] = []
        seen_ids: set[str] = set()
        category_errors: list[str] = []
        per_category_limit = max(20, min(80, limit // max(1, len(categories)) + 12))

        for category in categories:
            cat_query = self._build_query(
                city.min_lat,
                city.min_lon,
                city.max_lat,
                city.max_lon,
                [category],
                out_limit=max(60, per_category_limit * 4),
            )
            cat_result = self._run_overpass_query(cat_query, [category], per_category_limit)
            if not cat_result.ok:
                category_errors.append(f"{category}: {cat_result.error}")
                continue
            for poi in cat_result.data or []:
                if poi.poi_id in seen_ids:
                    continue
                seen_ids.add(poi.poi_id)
                merged.append(poi)
                if len(merged) >= limit:
                    break
            if len(merged) >= limit:
                break

        if merged:
            warning = None
            if primary.error or category_errors:
                warning = "; ".join([x for x in [primary.error, *category_errors] if x])
            return ToolResult(ok=True, data=merged, error=warning, latency_ms=self._elapsed_ms(started))

        combined_errors = "; ".join([x for x in [primary.error, *category_errors] if x]) or "overpass empty response"
        return ToolResult(ok=False, error=combined_errors, latency_ms=self._elapsed_ms(started))

    def _run_overpass_query(self, query: str, categories: list[str], limit: int) -> ToolResult:
        errors: list[str] = []

        for endpoint in OVERPASS_ENDPOINTS:
            payload = urllib.parse.urlencode({"data": query}).encode("utf-8")
            req = urllib.request.Request(
                endpoint,
                data=payload,
                method="POST",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
                    "User-Agent": "CityExplorerAgent/0.1 (student-poc)",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=max(TOOL_TIMEOUT_SEC, 18)) as resp:
                    body = resp.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                errors.append(f"{endpoint}: HTTP {e.code}")
                continue
            except urllib.error.URLError as e:
                errors.append(f"{endpoint}: {e}")
                continue
            except TimeoutError:
                errors.append(f"{endpoint}: timeout")
                continue

            try:
                data = json.loads(body)
                elements = data.get("elements", [])
            except json.JSONDecodeError:
                errors.append(f"{endpoint}: invalid json")
                continue

            normalized = self._normalize_elements(elements, categories, limit)
            return ToolResult(ok=True, data=normalized)

        return ToolResult(ok=False, error="overpass network error: " + " | ".join(errors))

    def _normalize_elements(self, elements: list[dict[str, Any]], categories: list[str], limit: int) -> list[POI]:
        normalized: list[POI] = []
        for elem in elements:
            tags = elem.get("tags") or {}
            category = self._category_from_tags(tags)
            if category not in categories:
                continue
            lat = elem.get("lat") or (elem.get("center") or {}).get("lat")
            lon = elem.get("lon") or (elem.get("center") or {}).get("lon")
            if lat is None or lon is None:
                continue
            normalized.append(
                POI(
                    poi_id=f"osm:{elem.get('type', 'node')}:{elem.get('id', 'na')}",
                    name=tags.get("name") or f"Unnamed {category}",
                    lat=float(lat),
                    lon=float(lon),
                    category=category,
                    tags=tags,
                    source="overpass",
                )
            )
            if len(normalized) >= limit:
                break
        return normalized

    def _fetch_sample(self, city: CityResolution, categories: list[str], limit: int) -> list[POI]:
        if not SAMPLE_DATA_PATH.exists():
            return []

        raw = json.loads(SAMPLE_DATA_PATH.read_text(encoding="utf-8"))
        keys = [city.canonical_name.lower(), city.query.lower()]

        items: list[dict[str, Any]] = []
        for key in keys:
            if key in raw:
                items = raw[key]
                break

        out: list[POI] = []
        for item in items:
            category = str(item.get("category", "")).lower()
            if category not in categories:
                continue
            out.append(
                POI(
                    poi_id=str(item.get("id")),
                    name=str(item.get("name")),
                    lat=float(item.get("lat")),
                    lon=float(item.get("lon")),
                    category=category,
                    tags=item.get("tags") or {},
                    source="sample",
                    description=str(item.get("description") or ""),
                    photo_url=str(item.get("photo_url") or ""),
                    wiki_url=str(item.get("wiki_url") or ""),
                )
            )
            if len(out) >= limit:
                break
        return out

    def _build_query(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        categories: list[str],
        out_limit: int = 120,
    ) -> str:
        timeout_sec = max(14, TOOL_TIMEOUT_SEC + 8)
        out_limit = max(50, min(out_limit, 400))
        lines = [f"[out:json][timeout:{timeout_sec}];", "("]
        for category in categories:
            osm_filter = CATEGORY_TO_OSM_FILTER.get(category)
            if not osm_filter:
                continue
            key, val = osm_filter.split("=", 1)
            lines.append(f'  nwr["{key}"="{val}"]({min_lat},{min_lon},{max_lat},{max_lon});')
        lines.extend([");", f"out center {out_limit};"])
        return "\n".join(lines)

    def _category_from_tags(self, tags: dict[str, Any]) -> str:
        if tags.get("tourism") == "museum":
            return "museum"
        if tags.get("leisure") == "park":
            return "park"
        if tags.get("amenity") == "cafe":
            return "cafe"
        if tags.get("tourism") == "viewpoint":
            return "viewpoint"
        if tags.get("historic") == "monument":
            return "landmark"
        if tags.get("tourism") == "gallery":
            return "gallery"
        if tags.get("amenity") == "theatre":
            return "theatre"
        if tags.get("shop") == "mall":
            return "shopping"
        if tags.get("amenity") == "library":
            return "library"
        if tags.get("natural") == "beach":
            return "beach"
        if tags.get("amenity") == "bar":
            return "bar"
        if tags.get("amenity") == "hookah_lounge":
            return "hookah"
        return "unknown"

    def _cache_key(self, city: CityResolution, categories: list[str]) -> str:
        bbox_key = f"{city.min_lat:.3f}:{city.min_lon:.3f}:{city.max_lat:.3f}:{city.max_lon:.3f}"
        return f"{city.canonical_name.lower()}::{bbox_key}::{','.join(sorted(categories))}"

    def _build_synthetic_fallback(self, city: CityResolution, categories: list[str], limit: int) -> list[POI]:
        if limit <= 0:
            return []

        templates: dict[str, tuple[str, str, str]] = {
            "museum": (
                "City Museum",
                "Ключевой городской музей с экспозицией по истории и культуре.",
                "https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/Museum_icon.svg/512px-Museum_icon.svg.png",
            ),
            "park": (
                "Central Park",
                "Большой городской парк для прогулок и короткого отдыха.",
                "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/OOjs_UI_icon_mapPin-progressive.svg/512px-OOjs_UI_icon_mapPin-progressive.svg.png",
            ),
            "cafe": (
                "Local Coffee Spot",
                "Популярная кофейня в центре города с быстрым сервисом.",
                "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/Coffee_cup_icon.svg/512px-Coffee_cup_icon.svg.png",
            ),
            "viewpoint": (
                "Panorama Viewpoint",
                "Точка обзора с хорошим видом на центральные кварталы.",
                "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Map_marker.svg/512px-Map_marker.svg.png",
            ),
            "landmark": (
                "Historic Landmark",
                "Знаковый объект города, часто попадает в туристические маршруты.",
                "https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/Monument_icon.svg/512px-Monument_icon.svg.png",
            ),
            "gallery": (
                "Art Gallery",
                "Небольшая галерея современного и локального искусства.",
                "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Icon_Art.svg/512px-Icon_Art.svg.png",
            ),
            "theatre": (
                "City Theatre",
                "Театральная площадка с регулярной вечерней программой.",
                "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Theater-masks.svg/512px-Theater-masks.svg.png",
            ),
            "shopping": (
                "Main Shopping Mall",
                "Крупный торговый центр с зонами отдыха.",
                "https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Shopping_cart_icon.svg/512px-Shopping_cart_icon.svg.png",
            ),
            "library": (
                "Public Library",
                "Центральная библиотека с тихими залами и чтением на месте.",
                "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f0/Icon-book.svg/512px-Icon-book.svg.png",
            ),
            "beach": (
                "City Beach",
                "Оборудованная зона у воды для спокойного отдыха.",
                "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Weather-few-clouds.svg/512px-Weather-few-clouds.svg.png",
            ),
            "bar": (
                "Popular Bar Area",
                "Район с барами и вечерней активностью.",
                "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Wikimania2016_icons_-_Cocktail.svg/512px-Wikimania2016_icons_-_Cocktail.svg.png",
            ),
            "hookah": (
                "Hookah Lounge Zone",
                "Зона с кальянными заведениями.",
                "https://upload.wikimedia.org/wikipedia/commons/thumb/8/84/No_smoking_symbol.svg/512px-No_smoking_symbol.svg.png",
            ),
        }

        offsets = [
            (0.0050, 0.0035),
            (-0.0040, 0.0060),
            (0.0065, -0.0045),
            (-0.0060, -0.0030),
            (0.0030, 0.0070),
            (-0.0035, -0.0065),
        ]

        out: list[POI] = []
        used_categories = [c for c in categories if c in templates]
        if not used_categories:
            used_categories = ["museum", "park", "cafe"]

        for idx, category in enumerate(used_categories):
            if len(out) >= limit:
                break
            dlat, dlon = offsets[idx % len(offsets)]
            title, description, photo_url = templates[category]
            out.append(
                POI(
                    poi_id=f"synthetic:{city.canonical_name.lower().replace(' ', '_')}:{idx + 1}",
                    name=f"{city.canonical_name} {title}",
                    lat=city.center_lat + dlat,
                    lon=city.center_lon + dlon,
                    category=category,
                    tags={"synthetic": "true"},
                    source="synthetic",
                    description=description,
                    photo_url=photo_url,
                    wiki_url=f"https://en.wikipedia.org/wiki/{city.canonical_name.replace(' ', '_')}",
                )
            )

        return out

    def _load_from_cache(self, key: str) -> list[POI]:
        if not self.cache_path.exists():
            return []
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        entry = payload.get(key)
        if not entry:
            return []

        if int(time.time()) - int(entry.get("ts", 0)) > RETRIEVER_CACHE_TTL_SEC:
            return []

        out: list[POI] = []
        for item in entry.get("data", []):
            out.append(
                POI(
                    poi_id=item["poi_id"],
                    name=item["name"],
                    lat=float(item["lat"]),
                    lon=float(item["lon"]),
                    category=item["category"],
                    tags=item.get("tags") or {},
                    source=item.get("source", "cache"),
                    description=item.get("description") or "",
                    photo_url=item.get("photo_url") or "",
                    wiki_url=item.get("wiki_url") or "",
                )
            )
        return out

    def _save_to_cache(self, key: str, pois: list[POI]) -> None:
        payload: dict[str, Any] = {}
        if self.cache_path.exists():
            try:
                payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {}

        payload[key] = {
            "ts": int(time.time()),
            "data": [
                {
                    "poi_id": p.poi_id,
                    "name": p.name,
                    "lat": p.lat,
                    "lon": p.lon,
                    "category": p.category,
                    "tags": p.tags,
                    "source": p.source,
                    "description": p.description,
                    "photo_url": p.photo_url,
                    "wiki_url": p.wiki_url,
                }
                for p in pois
            ],
        }
        self.cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _elapsed_ms(self, started: float) -> int:
        return int((time.perf_counter() - started) * 1000)
