# db.py
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime

DB_PATH = "queue.db"
_lock = threading.Lock()
_conn = None
TIMEFMT = "%Y-%m-%dT%H:%M:%SZ"

def init_db():
    global _conn
    with _lock:
        if _conn:
            return
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False, isolation_level=None)
        _conn.execute("PRAGMA journal_mode=WAL;")
        _conn.execute("PRAGMA synchronous=NORMAL;")
        migrate()

def migrate():
    c = _conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        command TEXT NOT NULL,
        state TEXT NOT NULL,
        attempts INTEGER NOT NULL,
        max_retries INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        lock_owner TEXT,
        next_retry_at TEXT,
        last_error TEXT,
        output TEXT
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_state_nextretry ON jobs(state, next_retry_at)")
    c.close()

@contextmanager
def get_cursor():
    if _conn is None:
        init_db()
    cur = _conn.cursor()
    try:
        yield cur
    finally:
        cur.close()
