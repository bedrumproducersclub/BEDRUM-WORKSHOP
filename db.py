import sqlite3
from typing import Optional, Dict, Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY,
  username TEXT,
  first_name_input TEXT,
  last_name_input TEXT,
  phone TEXT,
  status TEXT DEFAULT 'STARTED',
  receipt_file_id TEXT,
  receipt_type TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_updated_at ON users(updated_at DESC);
"""

class DB:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.executescript(SCHEMA)

    def upsert_user(self, user_id: int, username: Optional[str] = None) -> None:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO users (user_id, username)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
              username=COALESCE(?, users.username),
              updated_at=CURRENT_TIMESTAMP
        """, (user_id, username, username))
        self.conn.commit()

    def set_field(self, user_id: int, field: str, value: Any) -> None:
        q = f"UPDATE users SET {field}=?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?"
        self.conn.execute(q, (value, user_id))
        self.conn.commit()

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT user_id, username, first_name_input, last_name_input, phone, status, receipt_file_id, receipt_type FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        keys = ["user_id","username","first_name_input","last_name_input","phone","status","receipt_file_id","receipt_type"]
        return dict(zip(keys, row))

    def all_users(self):
        cur = self.conn.cursor()
        cur.execute("SELECT user_id, username, first_name_input, last_name_input, phone, status, receipt_file_id, receipt_type FROM users ORDER BY updated_at DESC")
        rows = cur.fetchall()
        keys = ["user_id","username","first_name_input","last_name_input","phone","status","receipt_file_id","receipt_type"]
        return [dict(zip(keys, r)) for r in rows]

    def delete_user(self, user_id: int) -> None:
        self.conn.execute("DELETE FROM users WHERE user_id=?", (user_id,))
        self.conn.commit()
