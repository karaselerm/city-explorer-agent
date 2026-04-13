from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from .city_resolver import CityResolver
from .config import (
    DEFAULT_CATEGORIES,
    RETRIEVER_FALLBACK_MIN_CANDIDATES,
    TRANSPORT_LABELS,
    ensure_dirs,
    normalize_category_name,
)
from .enrichment import POIEnricher
from .memory import MemoryStore
from .models import POI, RoutePlan, TraceEvent, UserRequest
from .observability import EventLogger
from .ranker import POIRanker
from .retriever import POIRetriever
from .router import RouteBuilder
from .safety import SafetyGuard


@dataclass(slots=True)
class OrchestratorResult:
    request_id: str
    plan: RoutePlan | None
    trace: list[TraceEvent] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    used_fallback: bool = False


@dataclass(slots=True)
class CityExplorerOrchestrator:
    retriever: POIRetriever = field(default_factory=POIRetriever)
    ranker: POIRanker = field(default_factory=POIRanker)
    router: RouteBuilder = field(default_factory=RouteBuilder)
    city_resolver: CityResolver = field(default_factory=CityResolver)
    enricher: POIEnricher = field(default_factory=POIEnricher)
    memory: MemoryStore = field(default_factory=MemoryStore)
    logger: EventLogger = field(default_factory=EventLogger)
    safety: SafetyGuard = field(default_factory=SafetyGuard)

    def __post_init__(self) -> None:
        ensure_dirs()

    def run(self, req: UserRequest) -> OrchestratorResult:
        request_id = uuid.uuid4().hex[:8]
        trace: list[TraceEvent] = []
        errors: list[str] = []
        used_fallback = False

        started = self.logger.begin_request(request_id)

        safety_result = self.safety.validate_request(req)
        if not safety_result.ok:
            errors.append(safety_result.reason)
            trace.append(TraceEvent(step="safety_check", ok=False, meta={"reason": safety_result.reason}))
            self.logger.end_request(request_id, started, ok=False, used_fallback=False)
            return OrchestratorResult(request_id=request_id, plan=None, trace=trace, errors=errors)
        trace.append(TraceEvent(step="safety_check", ok=True))

        category_conflicts = self._normalize_and_reconcile_categories(req)

        prefs = self.memory.get_preferences(req.user_id)
        trace.append(TraceEvent(step="memory_load", ok=True, meta={"has_profile": bool(prefs)}))

        city_result = self.city_resolver.resolve(req.city)
        if not city_result.ok:
            error_message = city_result.error or "city resolve failed"
            suggestions = ((city_result.data or {}).get("suggestions") or [])
            if suggestions:
                error_message = f"{error_message}. Suggestions: {', '.join(suggestions)}"
            errors.append(error_message)
            trace.append(
                TraceEvent(
                    step="city_resolve",
                    ok=False,
                    meta={"query": req.city, "suggestions": suggestions},
                )
            )
            self.logger.end_request(request_id, started, ok=False, used_fallback=False)
            return OrchestratorResult(request_id=request_id, plan=None, trace=trace, errors=errors)
        city = city_result.data
        trace.append(
            TraceEvent(
                step="city_resolve",
                ok=True,
                meta={
                    "query": city.query,
                    "canonical_name": city.canonical_name,
                    "country": city.country,
                    "has_warning": bool(city.warning),
                },
            )
        )

        categories = req.must_categories or prefs.get("preferred_categories") or DEFAULT_CATEGORIES
        retrieve = self.retriever.fetch(req.city, categories, city_resolution=city)
        self.logger.log_tool(request_id, "poi_retriever", retrieve.ok, retrieve.latency_ms, retrieve.error or "")

        if not retrieve.ok:
            errors.append(retrieve.error or "retriever failed")
            trace.append(TraceEvent(step="retrieve_poi", ok=False, meta={"error": retrieve.error}))
            self.logger.end_request(request_id, started, ok=False, used_fallback=False)
            return OrchestratorResult(request_id=request_id, plan=None, trace=trace, errors=errors)

        candidates = retrieve.data or []
        if retrieve.error:
            used_fallback = True
            errors.append(f"retriever_fallback: {retrieve.error}")

        trace.append(
            TraceEvent(
                step="retrieve_poi",
                ok=True,
                meta={"candidate_count": len(candidates), "categories": categories},
            )
        )

        if len(candidates) < RETRIEVER_FALLBACK_MIN_CANDIDATES:
            used_fallback = True
            trace.append(
                TraceEvent(
                    step="relax_constraints",
                    ok=True,
                    meta={"reason": "too_few_candidates", "from": categories, "to": DEFAULT_CATEGORIES},
                )
            )
            retry = self.retriever.fetch(req.city, DEFAULT_CATEGORIES, city_resolution=city)
            self.logger.log_tool(request_id, "poi_retriever_retry", retry.ok, retry.latency_ms, retry.error or "")
            if retry.ok and retry.data:
                candidates = retry.data

        ranked = self.ranker.rank(candidates, req)
        if not ranked:
            errors.append("ranker filtered all candidates")
            trace.append(TraceEvent(step="rank_filter", ok=False, meta={"candidate_count": len(candidates)}))
            self.logger.end_request(request_id, started, ok=False, used_fallback=used_fallback)
            return OrchestratorResult(request_id=request_id, plan=None, trace=trace, errors=errors, used_fallback=used_fallback)

        trace.append(
            TraceEvent(
                step="rank_filter",
                ok=True,
                meta={"ranked_count": len(ranked), "top_score": round(ranked[0].score, 3)},
            )
        )

        try:
            plan = self.router.build(req, ranked, city)
            trace.append(TraceEvent(step="build_route", ok=True, meta={"stops": len(plan.stops)}))
        except Exception as e:  # noqa: BLE001
            used_fallback = True
            errors.append(f"route_builder_error: {e}")
            plan = RoutePlan(city=city.canonical_name, total_distance_km=0.0, total_duration_minutes=0, stops=[])
            # Fallback: top-3 ranked points without route optimization.
            for i, item in enumerate(ranked[:3], start=1):
                from .models import RouteStop

                plan.stops.append(
                    RouteStop(
                        order=i,
                        poi=item.poi,
                        walk_distance_km_from_prev=0.0,
                        eta_minutes_from_prev=0,
                        dwell_minutes=20,
                    )
                )
            plan.warnings.append("routing failed, using fallback static order")
            trace.append(TraceEvent(step="build_route", ok=False, meta={"error": str(e)}))

        if req.with_plan_b:
            used_ids = {stop.poi.poi_id for stop in plan.stops}
            plan.alternatives = [item.poi for item in ranked if item.poi.poi_id not in used_ids][:3]
        else:
            plan.alternatives = []
        self._enrich_plan_pois(plan, city.canonical_name)

        if category_conflicts:
            plan.warnings.append(
                "Категории в must и avoid одновременно: "
                + ", ".join(category_conflicts)
                + ". Приоритет отдан must."
            )

        if city.warning:
            plan.warnings.append(city.warning)

        plan.explanation = self._build_explanation(req, plan, ranked)
        if errors:
            plan.warnings.extend(errors)

        self._update_memory(req, plan)
        trace.append(TraceEvent(step="memory_update", ok=True))

        self.logger.end_request(request_id, started, ok=True, used_fallback=used_fallback)
        return OrchestratorResult(
            request_id=request_id,
            plan=plan,
            trace=trace,
            errors=errors,
            used_fallback=used_fallback,
        )

    def _enrich_plan_pois(self, plan: RoutePlan, city_name: str) -> None:
        pois: list[POI] = [stop.poi for stop in plan.stops]
        pois.extend(plan.alternatives)
        self.enricher.enrich(pois, city_name, limit=10)

    def _update_memory(self, req: UserRequest, plan: RoutePlan) -> None:
        profile = self.memory.get_preferences(req.user_id)
        preferred_categories = profile.get("preferred_categories", [])
        for category in req.must_categories:
            if category not in preferred_categories:
                preferred_categories.append(category)

        profile["preferred_categories"] = preferred_categories
        profile["last_city"] = req.city
        profile["last_budget"] = req.budget
        self.memory.upsert_preferences(req.user_id, profile)

        route_dump = {
            "distance_km": plan.total_distance_km,
            "duration_minutes": plan.total_duration_minutes,
            "stops": [
                {"name": s.poi.name, "category": s.poi.category, "lat": s.poi.lat, "lon": s.poi.lon}
                for s in plan.stops
            ],
            "warnings": plan.warnings,
        }
        self.memory.append_route(req.user_id, req.city, route_dump)

    def _build_explanation(self, req: UserRequest, plan: RoutePlan, ranked: list[Any]) -> str:
        category_map = {
            "museum": "музей",
            "park": "парк",
            "cafe": "кафе",
            "viewpoint": "смотровая площадка",
            "landmark": "достопримечательность",
            "gallery": "галерея",
            "theatre": "театр",
            "shopping": "шопинг",
            "library": "библиотека",
            "beach": "пляж",
            "bar": "бар",
            "hookah": "кальянная",
        }
        category_mix = ", ".join(sorted({category_map.get(stop.poi.category, stop.poi.category) for stop in plan.stops})) or "нет"
        top_reason = ""
        if ranked:
            reasons = ranked[0].reasons
            top_reason = reasons[0] if reasons else "высокий итоговый балл"

        transport_label = TRANSPORT_LABELS.get(req.transport_mode, TRANSPORT_LABELS["walk"])
        return (
            f"Маршрут построен под город '{plan.city}' ({transport_label}), лимит {req.duration_hours} ч и {req.max_distance_km} км. "
            f"Текущий набор категорий: {category_mix}. Главный критерий отбора: {top_reason}. "
            "Порядок остановок рассчитан эвристикой ближайшей точки и адаптирован под выбранный способ передвижения."
        )

    def _normalize_and_reconcile_categories(self, req: UserRequest) -> list[str]:
        def _unique(values: list[str]) -> list[str]:
            out: list[str] = []
            seen: set[str] = set()
            for value in values:
                if value in seen:
                    continue
                seen.add(value)
                out.append(value)
            return out

        must = [c for c in (normalize_category_name(x) for x in req.must_categories) if c]
        avoid = [c for c in (normalize_category_name(x) for x in req.avoid_categories) if c]
        must = _unique(must)
        avoid = _unique(avoid)

        overlap = sorted(set(must).intersection(avoid))
        if overlap:
            avoid = [x for x in avoid if x not in overlap]

        req.must_categories = must
        req.avoid_categories = avoid
        return overlap
