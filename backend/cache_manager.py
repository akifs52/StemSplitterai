import os
import time
import shutil
import hashlib
import json
from pathlib import Path


class CacheManager:
    def __init__(self, cache_dir=None, max_age_hours=24):
        if cache_dir is None:
            cache_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..",
                "separated",
            )
        self.cache_dir = Path(cache_dir)
        self.max_age_sec = max_age_hours * 3600
        self.index_path = self.cache_dir / "_cache_index.json"
        self._index = self._load_index()

    def _load_index(self):
        if self.index_path.exists():
            try:
                return json.loads(self.index_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_index(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(self._index, indent=2))

    def has_cached(self, file_path):
        key = self._make_key(file_path)
        entry = self._index.get(key)
        if entry and os.path.isdir(entry.get("path", "")):
            entry["last_access"] = time.time()
            self._save_index()
            return entry["path"]
        return None

    def set_cached(self, original_path, output_path):
        key = self._make_key(original_path)
        self._index[key] = {
            "original": original_path,
            "path": output_path,
            "created": time.time(),
            "last_access": time.time(),
            "size": self._dir_size(output_path) if os.path.isdir(output_path) else 0,
        }
        self._save_index()

    def _make_key(self, file_path):
        stat = os.stat(file_path)
        raw = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _dir_size(self, path):
        total = 0
        for entry in os.scandir(path):
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += self._dir_size(entry.path)
        return total

    def cleanup(self):
        now = time.time()
        expired_keys = []
        for key, entry in self._index.items():
            age = now - entry.get("created", 0)
            if age > self.max_age_sec:
                expired_keys.append(key)
                cached_path = entry.get("path")
                if cached_path and os.path.isdir(cached_path):
                    shutil.rmtree(cached_path, ignore_errors=True)
        for key in expired_keys:
            del self._index[key]
        if expired_keys:
            self._save_index()
        return len(expired_keys)
