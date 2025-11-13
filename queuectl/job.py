# job.py
import json
import sqlite3
from datetime import datetime
from db import get_cursor, init_db, TIMEFMT
from typing import Optional

init_db()

class Job:
    def __init__(self, id: str, command: str, state='pending', attempts=0, max_retries=3,
                 created_at=None, updated_at=None, last_error=None, output=None):
        self.id = id
        self.command = command
        self.state = state
        self.attempts = attempts
        self.max_retries = max_retries
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.last_error = last_error
        self.output = output

    def to_dict(self):
        return {
            "id": self.id,
            "command": self.command,
            "state": self.state,
            "attempts": self.attempts,
            "max_retries": self.max_retries,
            "created_at": self.created_at.strftime(TIMEFMT),
            "updated_at": self.updated_at.strftime(TIMEFMT),
            "last_error": self.last_error,
            "output": self.output,
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    @staticmethod
    def from_json_bytes(b: bytes):
        d = json.loads(b)
        fmt = TIMEFMT
        ca = datetime.strptime(d.get("created_at"), fmt) if d.get("created_at") else datetime.utcnow()
        ua = datetime.strptime(d.get("updated_at"), fmt) if d.get("updated_at") else datetime.utcnow()
        return Job(
            id=d.get("id"),
            command=d["command"],
            state=d.get("state", "pending"),
            attempts=d.get("attempts", 0),
            max_retries=d.get("max_retries", 3),
            created_at=ca,
            updated_at=ua
        )

def enqueue(job: Job):
    with get_cursor() as c:
        c.execute("""INSERT INTO jobs (id,command,state,attempts,max_retries,created_at,updated_at,next_retry_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (job.id, job.command, job.state, job.attempts, job.max_retries,
                   job.created_at.strftime(TIMEFMT), job.updated_at.strftime(TIMEFMT),
                   job.created_at.strftime(TIMEFMT)))
        c.connection.commit()

def list_jobs(state: Optional[str] = None):
    q = "SELECT id,command,state,attempts,max_retries,created_at,updated_at,last_error,output FROM jobs"
    args = []
    if state:
        q += " WHERE state=?"
        args.append(state)
    q += " ORDER BY created_at"
    with get_cursor() as c:
        cur = c.execute(q, args)
        rows = cur.fetchall()
    res = []
    for r in rows:
        res.append({
            "id": r[0], "command": r[1], "state": r[2], "attempts": r[3],
            "max_retries": r[4], "created_at": r[5], "updated_at": r[6],
            "last_error": r[7], "output": r[8]
        })
    return res

def get_summary():
    with get_cursor() as c:
        row = c.execute("""
        SELECT
         SUM(CASE WHEN state='pending' THEN 1 ELSE 0 END),
         SUM(CASE WHEN state='processing' THEN 1 ELSE 0 END),
         SUM(CASE WHEN state='completed' THEN 1 ELSE 0 END),
         SUM(CASE WHEN state='failed' THEN 1 ELSE 0 END),
         SUM(CASE WHEN state='dead' THEN 1 ELSE 0 END)
        FROM jobs
        """).fetchone()
    return {
        "pending": row[0] or 0,
        "processing": row[1] or 0,
        "completed": row[2] or 0,
        "failed": row[3] or 0,
        "dead": row[4] or 0,
    }

def claim_next_pending(worker_id: str):
    now = datetime.utcnow().strftime(TIMEFMT)
    with get_cursor() as c:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("""SELECT id,command,attempts,max_retries FROM jobs
                         WHERE state='pending' AND (next_retry_at IS NULL OR next_retry_at <= ?)
                         ORDER BY created_at LIMIT 1""", (now,)).fetchone()
        if not row:
            c.execute("COMMIT")
            return None
        job_id = row[0]
        res = c.execute("UPDATE jobs SET state='processing', lock_owner=?, updated_at=? WHERE id=? AND state='pending'",
                        (worker_id, now, job_id))
        if res.rowcount == 0:
            c.execute("ROLLBACK")
            return None
        c.execute("COMMIT")
        return {
            "id": job_id,
            "command": row[1],
            "attempts": row[2],
            "max_retries": row[3]
        }

def mark_completed(job_id: str, output: str):
    now = datetime.utcnow().strftime(TIMEFMT)
    with get_cursor() as c:
        c.execute("UPDATE jobs SET state='completed', updated_at=?, output=? WHERE id=?", (now, output, job_id))
        c.connection.commit()

def mark_failed_with_retry(job_id: str, attempts: int, last_err: str, next_retry_iso: str):
    now = datetime.utcnow().strftime(TIMEFMT)
    with get_cursor() as c:
        c.execute("""UPDATE jobs SET state='failed', attempts=?, last_error=?, next_retry_at=?, updated_at=? WHERE id=?""",
                  (attempts, last_err, next_retry_iso, now, job_id))
        c.connection.commit()

def move_to_dead(job_id: str, last_err: str):
    now = datetime.utcnow().strftime(TIMEFMT)
    with get_cursor() as c:
        c.execute("UPDATE jobs SET state='dead', last_error=?, updated_at=? WHERE id=?", (last_err, now, job_id))
        c.connection.commit()

def retry_dlq(job_id: str):
    now = datetime.utcnow().strftime(TIMEFMT)
    with get_cursor() as c:
        cur = c.execute("UPDATE jobs SET state='pending', attempts=0, next_retry_at=?, updated_at=? WHERE id=? AND state='dead'",
                        (now, now, job_id))
        c.connection.commit()
        return cur.rowcount > 0
