from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from difflib import SequenceMatcher

from .config import TOOL_TIMEOUT_SEC
from .models import POI

WIKI_LANGS = ["ru", "en"]


@dataclass(slots=True)
class POIEnricher:
    """Adds short description and photo URL so user does not need external search."""

    def enrich(self, pois: list[POI], city: str, limit: int = 8) -> None:
        for poi in pois[:limit]:
            if poi.description and poi.photo_url:
                continue
            self._enrich_one(poi, city)

    def _enrich_one(self, poi: POI, city: str) -> None:
        tag_description = str(poi.tags.get("description") or "").strip()
        if tag_description and not poi.description:
            poi.description = tag_description

        image = str(poi.tags.get("image") or "").strip()
        if image and not poi.photo_url:
            poi.photo_url = image

        wiki_tag = str(poi.tags.get("wikipedia") or "").strip()
        if wiki_tag:
            lang, _, title = wiki_tag.partition(":")
            if lang and title:
                summary = self._wiki_summary(lang, title)
                if summary:
                    self._apply_summary(poi, summary)
                    return

        for lang in WIKI_LANGS:
            title = self._wiki_search_title(lang, f"{poi.name} {city}")
            if not title:
                continue
            if not self._is_relevant_title(poi.name, title):
                continue
            summary = self._wiki_summary(lang, title)
            if summary:
                self._apply_summary(poi, summary)
                return

    def _wiki_search_title(self, lang: str, query: str) -> str:
        params = urllib.parse.urlencode(
            {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": query,
                "srlimit": 1,
                "utf8": 1,
            }
        )
        url = f"https://{lang}.wikipedia.org/w/api.php?{params}"
        payload = self._get_json(url)
        if not payload:
            return ""

        rows = ((payload.get("query") or {}).get("search") or [])
        if not rows:
            return ""
        return str(rows[0].get("title") or "")

    def _wiki_summary(self, lang: str, title: str) -> dict | None:
        encoded_title = urllib.parse.quote(title.replace(" ", "_"))
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"
        payload = self._get_json(url)
        if not payload:
            return None
        if payload.get("type") == "https://mediawiki.org/wiki/HyperSwitch/errors/not_found":
            return None
        return payload

    def _apply_summary(self, poi: POI, summary: dict) -> None:
        if not poi.description:
            raw = str(summary.get("extract") or "").strip()
            poi.description = raw[:320] + ("..." if len(raw) > 320 else "")

        thumb = (summary.get("thumbnail") or {}).get("source")
        if thumb and not poi.photo_url:
            poi.photo_url = str(thumb)

        wiki_url = ((summary.get("content_urls") or {}).get("desktop") or {}).get("page")
        if wiki_url and not poi.wiki_url:
            poi.wiki_url = str(wiki_url)

    def _get_json(self, url: str) -> dict | list | None:
        req = urllib.request.Request(url, headers={"User-Agent": "CityExplorerAgent/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=min(TOOL_TIMEOUT_SEC, 6)) as resp:
                payload = resp.read().decode("utf-8")
            data = json.loads(payload)
        except Exception:  # noqa: BLE001
            return None
        if isinstance(data, (dict, list)):
            return data
        return None

    def _is_relevant_title(self, poi_name: str, title: str) -> bool:
        name = self._normalize_text(poi_name)
        page = self._normalize_text(title)
        if not name or not page:
            return False

        ratio = SequenceMatcher(None, name, page).ratio()
        if ratio >= 0.45:
            return True

        tokens = [t for t in name.split() if len(t) >= 4]
        return any(t in page for t in tokens)

    def _normalize_text(self, value: str) -> str:
        lowered = value.lower()
        lowered = re.sub(r"[^a-zа-я0-9\s]", " ", lowered)
        lowered = re.sub(r"\s+", " ", lowered)
        return lowered.strip()
