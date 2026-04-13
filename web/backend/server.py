from __future__ import annotations

import json
import os
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from mimetypes import guess_type
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from city_explorer.config import POPULAR_CATEGORIES, TRANSPORT_LABELS, normalize_category_name
from city_explorer.exporter import PlanExporter
from city_explorer.models import RoutePlan, UserRequest
from city_explorer.orchestrator import CityExplorerOrchestrator
from city_explorer.safety import SafetyGuard

_ORCHESTRATOR = CityExplorerOrchestrator()
_EXPORTER = PlanExporter(Path("outputs"))
_GUARD = SafetyGuard()
_LOCK = threading.Lock()


def _normalize_categories(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = [normalize_category_name(x) for x in raw.split(",")]
        return [x for x in parts if x]
    if isinstance(raw, list):
        out: list[str] = []
        for item in raw:
            if item is None:
                continue
            text = normalize_category_name(str(item))
            if text:
                out.append(text)
        return out
    return []


def _build_user_request(payload: dict[str, Any]) -> UserRequest:
    return UserRequest(
        user_id=str(payload.get("user_id") or "web_user"),
        city=str(payload.get("city") or "moscow").strip(),
        duration_hours=float(payload.get("duration_hours") or 3.0),
        max_distance_km=float(payload.get("max_distance_km") or 6.0),
        must_categories=_normalize_categories(payload.get("must_categories")),
        avoid_categories=_normalize_categories(payload.get("avoid_categories")),
        style=str(payload.get("style") or "balanced"),
        budget=str(payload.get("budget") or "medium"),
        transport_mode=str(payload.get("transport_mode") or "walk"),
        quiet=bool(payload.get("quiet") or False),
        with_plan_b=bool(payload.get("with_plan_b", True)),
    )


def _plan_to_payload(plan: RoutePlan) -> dict[str, Any]:
    return {
        "city": plan.city,
        "transport_mode": plan.transport_mode,
        "city_meta": plan.city_meta,
        "map_overview_url": plan.map_overview_url,
        "total_distance_km": plan.total_distance_km,
        "total_duration_minutes": plan.total_duration_minutes,
        "stops": [
            {
                "order": s.order,
                "id": s.poi.poi_id,
                "name": s.poi.name,
                "category": s.poi.category,
                "lat": s.poi.lat,
                "lon": s.poi.lon,
                "description": s.poi.description,
                "photo_url": s.poi.photo_url,
                "wiki_url": s.poi.wiki_url,
                "walk_km": s.walk_distance_km_from_prev,
                "distance_km": s.distance_km_from_prev,
                "eta_min": s.eta_minutes_from_prev,
                "dwell_min": s.dwell_minutes,
                "travel_mode": s.travel_mode,
                "travel_instruction": s.travel_instruction,
                "segment_map_url": s.segment_map_url,
                "map_url": f"https://www.openstreetmap.org/?mlat={s.poi.lat}&mlon={s.poi.lon}#map=16/{s.poi.lat}/{s.poi.lon}",
            }
            for s in plan.stops
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


class CityExplorerAPIHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "service": "city-explorer-backend",
                    "version": "0.1.0",
                },
            )
            return

        if parsed.path == "/api/logs":
            q = parse_qs(parsed.query)
            lines = max(1, min(int((q.get("lines") or ["30"])[0]), 200))
            logs = self._tail_logs(lines)
            self._send_json(HTTPStatus.OK, {"lines": logs})
            return
        if parsed.path == "/api/meta":
            self._send_json(
                HTTPStatus.OK,
                {
                    "popular_categories": POPULAR_CATEGORIES,
                    "transport_modes": [{"id": k, "label": v} for k, v in TRANSPORT_LABELS.items()],
                },
            )
            return

        static_ok = self._try_send_static(parsed.path)
        if static_ok:
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/api/plan":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        payload = self._read_json_body()
        if payload is None:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return

        try:
            req = _build_user_request(payload)
        except Exception as exc:  # noqa: BLE001
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"invalid_request: {exc}"})
            return

        with _LOCK:
            result = _ORCHESTRATOR.run(req)

        if result.plan is None:
            self._send_json(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {
                    "request_id": result.request_id,
                    "errors": result.errors,
                    "trace": [{"step": t.step, "ok": t.ok, "meta": t.meta} for t in result.trace],
                },
            )
            return

        export_formats = _normalize_categories(payload.get("export_formats")) or ["markdown", "json"]
        if "md" in export_formats and "markdown" not in export_formats:
            export_formats.append("markdown")

        exports: list[str] = []
        for fmt in export_formats:
            if fmt == "markdown":
                exports.append(str(_EXPORTER.export_markdown(result.plan, result.request_id)))
            elif fmt == "json":
                exports.append(str(_EXPORTER.export_json(result.plan, result.request_id)))
            elif fmt == "ics":
                can_export = _GUARD.can_export_ics(bool(payload.get("confirm_side_effects", False)))
                if not can_export.ok:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": can_export.reason})
                    return
                exports.append(str(_EXPORTER.export_ics(result.plan, result.request_id)))

        response = {
            "request_id": result.request_id,
            "used_fallback": result.used_fallback,
            "plan": _plan_to_payload(result.plan),
            "trace": [{"step": t.step, "ok": t.ok, "meta": t.meta} for t in result.trace],
            "errors": result.errors,
            "exports": exports,
        }
        self._send_json(HTTPStatus.OK, response)

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _read_json_body(self) -> dict[str, Any] | None:
        try:
            raw_len = int(self.headers.get("Content-Length") or "0")
            body = self.rfile.read(raw_len) if raw_len > 0 else b"{}"
            decoded = body.decode("utf-8")
            payload = json.loads(decoded)
            if not isinstance(payload, dict):
                return None
            return payload
        except Exception:  # noqa: BLE001
            return None

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _tail_logs(self, lines: int) -> list[str]:
        path = Path("logs/events.jsonl")
        if not path.exists():
            return []
        all_lines = path.read_text(encoding="utf-8").splitlines()
        return all_lines[-lines:]

    def _try_send_static(self, raw_path: str) -> bool:
        static_root = Path("web/frontend").resolve()
        path = raw_path or "/"
        if path == "/":
            candidate = static_root / "index.html"
        else:
            safe = path.lstrip("/")
            candidate = static_root / safe

        try:
            resolved = candidate.resolve()
        except FileNotFoundError:
            return False
        if static_root not in resolved.parents and resolved != static_root:
            return False

        if not resolved.exists() or not resolved.is_file():
            return False

        content = resolved.read_bytes()
        content_type = guess_type(str(resolved))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)
        return True


def main() -> None:
    host = os.getenv("CITY_EXPLORER_HOST", "0.0.0.0")
    port = int(os.getenv("CITY_EXPLORER_PORT", "8000"))

    server = ThreadingHTTPServer((host, port), CityExplorerAPIHandler)
    print(f"CityExplorer backend started on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
