"""SQLite-backed persistence for incidents and webhook events."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from sentinelcall.config import PAGER0_DB_PATH


class Pager0Store:
    """Small SQLite wrapper for incident and webhook persistence."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = str(Path(db_path or PAGER0_DB_PATH))
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    service TEXT,
                    incident_type TEXT,
                    auth_req_id TEXT,
                    call_id TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    data_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_incidents_status
                    ON incidents(status, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_incidents_auth_req_id
                    ON incidents(auth_req_id);
                CREATE INDEX IF NOT EXISTS idx_incidents_call_id
                    ON incidents(call_id);

                CREATE TABLE IF NOT EXISTS webhook_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    verified INTEGER NOT NULL,
                    incident_id TEXT,
                    call_id TEXT,
                    received_at REAL NOT NULL,
                    payload_json TEXT NOT NULL
                );
                """
            )
            self._conn.commit()

    def upsert_incident(self, incident: dict[str, Any]) -> None:
        now = float(incident.get("updated_at", time.time()))
        created_at = float(incident.get("started_at", incident.get("created_at", now)))
        payload = json.dumps(incident)
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO incidents (
                    incident_id, status, service, incident_type, auth_req_id, call_id,
                    created_at, updated_at, data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(incident_id) DO UPDATE SET
                    status=excluded.status,
                    service=excluded.service,
                    incident_type=excluded.incident_type,
                    auth_req_id=excluded.auth_req_id,
                    call_id=excluded.call_id,
                    updated_at=excluded.updated_at,
                    data_json=excluded.data_json
                """,
                (
                    incident["incident_id"],
                    incident.get("status", "unknown"),
                    incident.get("service"),
                    incident.get("incident_type"),
                    incident.get("ciba_auth_req_id"),
                    incident.get("call_id"),
                    created_at,
                    now,
                    payload,
                ),
            )
            self._conn.commit()

    def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT data_json FROM incidents WHERE incident_id = ?",
                (incident_id,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row["data_json"])

    def list_incidents(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT data_json FROM incidents ORDER BY created_at ASC"
            ).fetchall()
        return [json.loads(row["data_json"]) for row in rows]

    def find_incident_by_auth_req_id(self, auth_req_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT data_json FROM incidents WHERE auth_req_id = ? ORDER BY updated_at DESC LIMIT 1",
                (auth_req_id,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row["data_json"])

    def find_incident_by_call_id(self, call_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT data_json FROM incidents WHERE call_id = ? ORDER BY updated_at DESC LIMIT 1",
                (call_id,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row["data_json"])

    def record_webhook_event(
        self,
        provider: str,
        event_type: str,
        payload: dict[str, Any],
        verified: bool,
        incident_id: str | None = None,
        call_id: str | None = None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO webhook_events (
                    provider, event_type, verified, incident_id, call_id, received_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    provider,
                    event_type,
                    1 if verified else 0,
                    incident_id,
                    call_id,
                    time.time(),
                    json.dumps(payload),
                ),
            )
            self._conn.commit()

    def list_webhook_events(self, provider: str | None = None) -> list[dict[str, Any]]:
        query = (
            "SELECT provider, event_type, verified, incident_id, call_id, received_at, payload_json "
            "FROM webhook_events"
        )
        params: tuple[Any, ...] = ()
        if provider:
            query += " WHERE provider = ?"
            params = (provider,)
        query += " ORDER BY received_at ASC"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()

        events: list[dict[str, Any]] = []
        for row in rows:
            events.append(
                {
                    "provider": row["provider"],
                    "event_type": row["event_type"],
                    "verified": bool(row["verified"]),
                    "incident_id": row["incident_id"],
                    "call_id": row["call_id"],
                    "received_at": row["received_at"],
                    "payload": json.loads(row["payload_json"]),
                }
            )
        return events


store = Pager0Store()
