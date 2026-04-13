from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import OUTPUT_DIR
from .exporter import PlanExporter
from .models import UserRequest
from .orchestrator import CityExplorerOrchestrator
from .safety import SafetyGuard


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CityExplorer Agent PoC")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--city", required=True, help="e.g. moscow, saint petersburg, riga")
    parser.add_argument("--duration-hours", type=float, default=3.0)
    parser.add_argument("--max-distance-km", type=float, default=6.0)
    parser.add_argument("--must-category", action="append", default=[])
    parser.add_argument("--avoid-category", action="append", default=[])
    parser.add_argument("--style", default="balanced", choices=["balanced", "culture", "nature"])
    parser.add_argument("--budget", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--transport-mode", default="walk", choices=["walk", "bike", "car", "transit"])
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--no-plan-b", action="store_true")
    parser.add_argument(
        "--export-format",
        action="append",
        default=[],
        choices=["markdown", "json", "ics"],
    )
    parser.add_argument("--confirm-side-effects", action="store_true")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    return parser.parse_args(argv)


def _route_to_dict(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    req = UserRequest(
        user_id=args.user_id,
        city=args.city,
        duration_hours=args.duration_hours,
        max_distance_km=args.max_distance_km,
        must_categories=args.must_category,
        avoid_categories=args.avoid_category,
        style=args.style,
        budget=args.budget,
        transport_mode=args.transport_mode,
        quiet=bool(args.quiet),
        with_plan_b=not bool(args.no_plan_b),
    )

    orchestrator = CityExplorerOrchestrator()
    result = orchestrator.run(req)

    if result.plan is None:
        print(_route_to_dict({"request_id": result.request_id, "errors": result.errors}), file=sys.stderr)
        return 2

    exporter = PlanExporter(Path(args.output_dir))
    exports: list[str] = []
    formats = list(dict.fromkeys(args.export_format or ["markdown", "json"]))

    for fmt in formats:
        if fmt == "markdown":
            exports.append(str(exporter.export_markdown(result.plan, result.request_id)))
        elif fmt == "json":
            exports.append(str(exporter.export_json(result.plan, result.request_id)))
        elif fmt == "ics":
            can_export = SafetyGuard().can_export_ics(args.confirm_side_effects)
            if not can_export.ok:
                print(_route_to_dict({"error": can_export.reason}), file=sys.stderr)
                return 3
            exports.append(str(exporter.export_ics(result.plan, result.request_id)))

    view = {
        "request_id": result.request_id,
        "city": result.plan.city,
        "stops": [
            {
                "order": s.order,
                "name": s.poi.name,
                "category": s.poi.category,
                "walk_km": s.walk_distance_km_from_prev,
                "eta_min": s.eta_minutes_from_prev,
            }
            for s in result.plan.stops
        ],
        "total_distance_km": result.plan.total_distance_km,
        "total_duration_minutes": result.plan.total_duration_minutes,
        "warnings": result.plan.warnings,
        "trace": [{"step": t.step, "ok": t.ok, "meta": t.meta} for t in result.trace],
        "exports": exports,
    }

    print(_route_to_dict(view))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
