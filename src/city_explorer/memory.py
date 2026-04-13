from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import RUNTIME_DIR


@dataclass(slots=True)
class MemoryStore:
    db_path: Path = RUNTIME_DIR / "memory.db"

    def __post_init__(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    preferences_json TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS route_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    city TEXT NOT NULL,
                    route_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_preferences(self, user_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT preferences_json FROM user_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if not row:
            return {}
        return json.loads(row["preferences_json"])

    def upsert_preferences(self, user_id: str, preferences: dict[str, Any]) -> None:
        payload = json.dumps(preferences, ensure_ascii=False)
        now = int(time.time())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_profiles(user_id, preferences_json, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                  preferences_json = excluded.preferences_json,
                  updated_at = excluded.updated_at
                """,
                (user_id, payload, now),
            )

    def append_route(self, user_id: str, city: str, route_json: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO route_history(user_id, city, route_json, created_at) VALUES(?, ?, ?, ?)",
                (user_id, city, json.dumps(route_json, ensure_ascii=False), int(time.time())),
            )
