from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import RoutePlan


@dataclass(slots=True)
class PlanExporter:
    output_dir: Path

    def export_markdown(self, plan: RoutePlan, request_id: str) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"route_{request_id}.md"

        lines: list[str] = [
            f"# Route Plan — {plan.city}",
            "",
            f"Transport mode: **{plan.transport_mode}**",
            f"Total duration: **{plan.total_duration_minutes} min**",
            f"Total distance: **{plan.total_distance_km} km**",
            "",
            "## Stops",
        ]

        for stop in plan.stops:
            osm_link = f"https://www.openstreetmap.org/?mlat={stop.poi.lat}&mlon={stop.poi.lon}#map=16/{stop.poi.lat}/{stop.poi.lon}"
            lines.extend(
                [
                    f"{stop.order}. **{stop.poi.name}** ({stop.poi.category})",
                    f"   - from previous: {stop.distance_km_from_prev} km / {stop.eta_minutes_from_prev} min",
                    f"   - move: {stop.travel_instruction}",
                    f"   - suggested stay: {stop.dwell_minutes} min",
                    f"   - map: {osm_link}",
                ]
            )
            if stop.poi.description:
                lines.append(f"   - description: {stop.poi.description}")
            if stop.poi.photo_url:
                lines.append(f"   - photo: {stop.poi.photo_url}")
            if stop.segment_map_url:
                lines.append(f"   - route segment: {stop.segment_map_url}")

        if plan.alternatives:
            lines.append("")
            lines.append("## Plan B")
            for alt in plan.alternatives:
                lines.append(f"- {alt.name} ({alt.category})")
                if alt.description:
                    lines.append(f"  - {alt.description}")
                if alt.photo_url:
                    lines.append(f"  - photo: {alt.photo_url}")

        if plan.warnings:
            lines.append("")
            lines.append("## Warnings")
            for w in plan.warnings:
                lines.append(f"- {w}")

        lines.append("")
        lines.append("## Why this plan")
        lines.append(plan.explanation)

        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def export_json(self, plan: RoutePlan, request_id: str) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"route_{request_id}.json"
        payload = {
            "city": plan.city,
            "transport_mode": plan.transport_mode,
            "map_overview_url": plan.map_overview_url,
            "city_meta": plan.city_meta,
            "total_distance_km": plan.total_distance_km,
            "total_duration_minutes": plan.total_duration_minutes,
            "stops": [
                {
                    "order": stop.order,
                    "id": stop.poi.poi_id,
                    "name": stop.poi.name,
                    "category": stop.poi.category,
                    "lat": stop.poi.lat,
                    "lon": stop.poi.lon,
                    "description": stop.poi.description,
                    "photo_url": stop.poi.photo_url,
                    "wiki_url": stop.poi.wiki_url,
                    "walk_distance_km_from_prev": stop.walk_distance_km_from_prev,
                    "distance_km_from_prev": stop.distance_km_from_prev,
                    "eta_minutes_from_prev": stop.eta_minutes_from_prev,
                    "dwell_minutes": stop.dwell_minutes,
                    "travel_mode": stop.travel_mode,
                    "travel_instruction": stop.travel_instruction,
                    "segment_map_url": stop.segment_map_url,
                }
                for stop in plan.stops
            ],
            "alternatives": [
                {
                    "id": p.poi_id,
                    "name": p.name,
                    "category": p.category,
                    "lat": p.lat,
                    "lon": p.lon,
                    "description": p.description,
                    "photo_url": p.photo_url,
                    "wiki_url": p.wiki_url,
                }
                for p in plan.alternatives
            ],
            "warnings": plan.warnings,
            "explanation": plan.explanation,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def export_ics(self, plan: RoutePlan, request_id: str) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"route_{request_id}.ics"

        start = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//CityExplorerAgent//EN",
        ]

        cursor = start
        for stop in plan.stops:
            begin = cursor
            end = begin + timedelta(minutes=stop.dwell_minutes)
            uid = f"{request_id}-{stop.order}@cityexplorer"
            lines.extend(
                [
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTAMP:{start.strftime('%Y%m%dT%H%M%SZ')}",
                    f"DTSTART:{begin.strftime('%Y%m%dT%H%M%SZ')}",
                    f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}",
                    f"SUMMARY:{stop.poi.name}",
                    f"DESCRIPTION:Category={stop.poi.category}; lat={stop.poi.lat}; lon={stop.poi.lon}",
                    "END:VEVENT",
                ]
            )
            cursor = end + timedelta(minutes=stop.eta_minutes_from_prev)

        lines.append("END:VCALENDAR")
        path.write_text("\n".join(lines), encoding="utf-8")
        return path
