import os
import sqlite3
import json
from datetime import datetime


class Database:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..",
                "stemsplitter.db",
            )
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                duration_sec REAL,
                status TEXT,
                stems TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                config TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        conn.close()

    def add_history(self, file_name, file_path, file_size, duration, status, stems):
        conn = self._connect()
        conn.execute(
            "INSERT INTO history (file_name, file_path, file_size, duration_sec, status, stems) VALUES (?,?,?,?,?,?)",
            (file_name, file_path, file_size, duration, status, json.dumps(stems)),
        )
        conn.commit()
        conn.close()

    def get_history(self, limit=50):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM history ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_setting(self, key, default=None):
        conn = self._connect()
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        conn.close()
        return row["value"] if row else default

    def set_setting(self, key, value):
        conn = self._connect()
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
        conn.commit()
        conn.close()

    def save_preset(self, name, config):
        conn = self._connect()
        conn.execute(
            "INSERT OR REPLACE INTO presets (name, config) VALUES (?, ?)",
            (name, json.dumps(config)),
        )
        conn.commit()
        conn.close()

    def get_presets(self):
        conn = self._connect()
        rows = conn.execute("SELECT * FROM presets ORDER BY created_at DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]
