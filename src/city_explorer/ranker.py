from __future__ import annotations

from dataclasses import dataclass

from .models import POI, RankedPOI, UserRequest


@dataclass(slots=True)
class POIRanker:
    def rank(self, pois: list[POI], req: UserRequest) -> list[RankedPOI]:
        ranked: list[RankedPOI] = []
        must = {c.lower() for c in req.must_categories}
        avoid = {c.lower() for c in req.avoid_categories}

        for poi in pois:
            category = poi.category.lower()
            if category in avoid:
                continue

            score = 0.0
            reasons: list[str] = []

            if must and category in must:
                score += 3.0
                reasons.append("соответствует обязательной категории")
            elif not must:
                score += 1.0

            if req.budget == "low" and poi.tags.get("price_level") in ("low", "free"):
                score += 1.5
                reasons.append("подходит под бюджет")
            elif req.budget == "high":
                score += 0.4

            if req.quiet and poi.tags.get("quiet") is True:
                score += 1.2
                reasons.append("тихая локация")

            if req.style == "culture" and category in {"museum", "landmark"}:
                score += 1.0
                reasons.append("подходит под культурный стиль")
            if req.style == "nature" and category == "park":
                score += 1.0
                reasons.append("подходит под природный стиль")

            if poi.tags.get("opening_hours"):
                score += 0.2
                reasons.append("есть данные о режиме работы")

            ranked.append(RankedPOI(poi=poi, score=score, reasons=reasons))

        ranked.sort(key=lambda x: x.score, reverse=True)
        return ranked
