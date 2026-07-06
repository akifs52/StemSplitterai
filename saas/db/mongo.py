from threading import Lock

from saas.core.config import get_settings
from saas.core.security import utcnow


class MemoryEventStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._events: list[dict] = []
        self._logs: list[dict] = []
        self._waveforms: dict[str, dict] = {}

    def append_event(self, job_id: str, event_type: str, payload: dict | None = None) -> None:
        with self._lock:
            self._events.append(
                {
                    "job_id": job_id,
                    "type": event_type,
                    "payload": payload or {},
                    "created_at": utcnow().isoformat(),
                }
            )

    def append_log(self, job_id: str, line: str) -> None:
        with self._lock:
            self._logs.append({"job_id": job_id, "line": line, "created_at": utcnow().isoformat()})

    def save_waveform(self, job_id: str, original: list, stems: dict) -> None:
        with self._lock:
            self._waveforms[job_id] = {
                "job_id": job_id,
                "original": original,
                "stems": stems,
                "updated_at": utcnow().isoformat(),
            }

    def list_events(self, job_id: str, limit: int = 200) -> list[dict]:
        with self._lock:
            rows = [item for item in self._events + self._logs if item["job_id"] == job_id]
        rows.sort(key=lambda item: item.get("created_at", ""))
        return rows[-limit:]

    def get_waveform(self, job_id: str) -> dict:
        with self._lock:
            return dict(self._waveforms.get(job_id, {}))


class MongoEventStore:
    def __init__(self) -> None:
        settings = get_settings()
        from pymongo import MongoClient

        self.client = MongoClient(settings.mongo_uri)
        self.db = self.client[settings.mongo_database]

    def append_event(self, job_id: str, event_type: str, payload: dict | None = None) -> None:
        self.db.job_events.insert_one(
            {
                "job_id": job_id,
                "type": event_type,
                "payload": payload or {},
                "created_at": utcnow(),
            }
        )

    def append_log(self, job_id: str, line: str) -> None:
        self.db.job_logs.insert_one({"job_id": job_id, "line": line, "created_at": utcnow()})

    def save_waveform(self, job_id: str, original: list, stems: dict) -> None:
        self.db.job_waveforms.update_one(
            {"job_id": job_id},
            {"$set": {"original": original, "stems": stems, "updated_at": utcnow()}},
            upsert=True,
        )

    def list_events(self, job_id: str, limit: int = 200) -> list[dict]:
        event_rows = list(
            self.db.job_events.find({"job_id": job_id}, {"_id": False}).sort("created_at", 1).limit(limit)
        )
        log_rows = list(
            self.db.job_logs.find({"job_id": job_id}, {"_id": False}).sort("created_at", 1).limit(limit)
        )
        rows = event_rows + log_rows
        rows.sort(key=lambda item: item.get("created_at"))
        for row in rows:
            value = row.get("created_at")
            if hasattr(value, "isoformat"):
                row["created_at"] = value.isoformat()
        return rows[-limit:]

    def get_waveform(self, job_id: str) -> dict:
        row = self.db.job_waveforms.find_one({"job_id": job_id}, {"_id": False}) or {}
        value = row.get("updated_at")
        if hasattr(value, "isoformat"):
            row["updated_at"] = value.isoformat()
        return row


_memory_store = MemoryEventStore()


def get_event_store():
    settings = get_settings()
    if settings.mongo_backend == "memory":
        return _memory_store
    return MongoEventStore()

