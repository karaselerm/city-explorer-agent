from __future__ import annotations

import difflib
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .config import HISTORICAL_CITY_ALIASES, PRESET_CITY_BOUNDS, TOOL_TIMEOUT_SEC
from .models import CityResolution, ToolResult

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


@dataclass(slots=True)
class CityResolver:
    def resolve(self, raw_city: str) -> ToolResult:
        query = (raw_city or "").strip()
        if not query:
            return ToolResult(ok=False, error="city is required")

        query_key = query.lower().strip()
        warning = ""
        canonical_query = query

        if query_key in HISTORICAL_CITY_ALIASES:
            canonical_query = HISTORICAL_CITY_ALIASES[query_key]
            warning = f"Название '{query}' устарело, использую актуальное: '{canonical_query.title()}'"

        preset = PRESET_CITY_BOUNDS.get(canonical_query.lower()) or PRESET_CITY_BOUNDS.get(query_key)
        if preset:
            min_lat, min_lon, max_lat, max_lon, center_lat, center_lon, country = preset
            return ToolResult(
                ok=True,
                data=CityResolution(
                    query=query,
                    canonical_name=canonical_query.title(),
                    country=country,
                    min_lat=min_lat,
                    min_lon=min_lon,
                    max_lat=max_lat,
                    max_lon=max_lon,
                    center_lat=center_lat,
                    center_lon=center_lon,
                    warning=warning,
                    suggestions=[],
                ),
            )

        search = self._search_nominatim(canonical_query)
        if not search.ok:
            return ToolResult(
                ok=False,
                error=search.error,
                data={"suggestions": self._build_suggestions(query)},
            )

        rows: list[dict[str, Any]] = search.data or []
        if not rows:
            return ToolResult(
                ok=False,
                error=f"city '{query}' not found",
                data={"suggestions": self._build_suggestions(query)},
            )

        chosen = self._pick_city_like_result(rows)
        if not chosen:
            return ToolResult(
                ok=False,
                error=f"city '{query}' not found as a current city",
                data={"suggestions": self._suggest_from_rows(rows)},
            )

        bbox = chosen.get("boundingbox") or []
        if len(bbox) != 4:
            return ToolResult(
                ok=False,
                error="failed to parse city bounding box",
                data={"suggestions": self._suggest_from_rows(rows)},
            )

        min_lat = float(bbox[0])
        max_lat = float(bbox[1])
        min_lon = float(bbox[2])
        max_lon = float(bbox[3])
        center_lat = float(chosen.get("lat"))
        center_lon = float(chosen.get("lon"))

        address = chosen.get("address") or {}
        country = str(address.get("country") or "unknown")
        display = str(chosen.get("display_name") or canonical_query)

        resolution = CityResolution(
            query=query,
            canonical_name=display.split(",")[0].strip(),
            country=country,
            min_lat=min_lat,
            min_lon=min_lon,
            max_lat=max_lat,
            max_lon=max_lon,
            center_lat=center_lat,
            center_lon=center_lon,
            warning=warning,
            suggestions=self._suggest_from_rows(rows),
        )
        return ToolResult(ok=True, data=resolution)

    def _search_nominatim(self, query: str) -> ToolResult:
        params = urllib.parse.urlencode(
            {
                "q": query,
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 6,
            }
        )
        req = urllib.request.Request(
            f"{NOMINATIM_URL}?{params}",
            headers={"User-Agent": "CityExplorerAgent/0.1 (student-poc)"},
        )

        try:
            with urllib.request.urlopen(req, timeout=TOOL_TIMEOUT_SEC) as resp:
                payload = resp.read().decode("utf-8")
        except urllib.error.URLError as e:
            return ToolResult(ok=False, error=f"city resolver network error: {e}")
        except TimeoutError:
            return ToolResult(ok=False, error="city resolver timeout")

        try:
            rows = json.loads(payload)
        except json.JSONDecodeError:
            return ToolResult(ok=False, error="invalid city resolver json")

        if not isinstance(rows, list):
            return ToolResult(ok=False, error="unexpected city resolver payload")

        return ToolResult(ok=True, data=rows)

    def _pick_city_like_result(self, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        city_like_types = {"city", "town", "village", "municipality", "administrative"}
        for row in rows:
            row_type = str(row.get("type") or "").lower()
            row_class = str(row.get("class") or "").lower()
            if row_type in city_like_types:
                return row
            if row_class == "boundary" and row_type == "administrative":
                return row
        return rows[0] if rows else None

    def _suggest_from_rows(self, rows: list[dict[str, Any]]) -> list[str]:
        out: list[str] = []
        for row in rows[:5]:
            display = str(row.get("display_name") or "").strip()
            if not display:
                continue
            city = display.split(",")[0].strip()
            if city and city not in out:
                out.append(city)
        return out

    def _build_suggestions(self, query: str) -> list[str]:
        pool = sorted(
            set(
                list(HISTORICAL_CITY_ALIASES.keys())
                + list(HISTORICAL_CITY_ALIASES.values())
                + list(PRESET_CITY_BOUNDS.keys())
            )
        )
        close = difflib.get_close_matches(query.lower(), pool, n=5, cutoff=0.55)
        return [item.title() for item in close]
