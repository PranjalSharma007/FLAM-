# FLAM-
FLAM  Assignment(BACKEND)
GITHUB REPO Link -> https://github.com/PranjalSharma007/FLAM-
## 📌 Overview

`queuectl` is a lightweight, CLI-based background job queue system implemented in **Python 3**.  
It supports:

- Enqueuing jobs  
- Worker execution  
- Automatic retries with exponential backoff  
- Dead Letter Queue (DLQ)  
- Persistent storage using SQLite  
- Configurable retry behavior  
- Full CLI interface  

This project was built as part of a backend engineering assignment.  
The system is fully functional and tested end-to-end.

---

## ⚙️ Architecture Overview

### 1. Core Components

| File | Purpose |
|------|---------|
| `main.py` | CLI entrypoint (enqueue, worker, dlq, config) |
| `worker.py` | Worker loop, SIGINT handling, job execution |
| `job.py` | SQLite job persistence layer |
| `db.py` | Database initialization & migrations |
| `config.py` | In-memory configuration store |
| `util.py` | Helpers (uuid, timestamps, etc.) |
| `test.sh` | Automated smoke test |

---

## 2. Job Lifecycle

A job transitions through:



pending → processing → (completed || failed)
Failed jobs retry automatically:
failed → pending (with next_retry_at)
After exceeding `max_retries`:

failed → dead (DLQ)
## 3. Retry Mechanism

Exponential backoff:

Example:

| attempts | delay (seconds) |
|---------|------------------|
| 1 | 2 |
| 2 | 4 |
| 3 | 8 |

---

# 🚀 Installation & Setup

### 1. Clone the project

```bash
git clone <your-repo-url>
cd queuectl


1) Create & activate virtual environment
cd ..
python3 -m venv .venv
source .venv/bin/activate
cd queuectl

Project structure:
FLAM/
   ├── .venv/
   └── queuectl/

../.venv/bin/python3


No external packages needed — only Python standard library.




🧪 Running a Worker
../.venv/bin/python3 main.py worker start --count 1 --poll 1


📥 Enqueue Jobs
../.venv/bin/python3 main.py enqueue '{"command": "echo hello; sleep 1", "max_retries": 2}'

📊 Check Status

../.venv/bin/python3 main.py status

🗂️ List Jobs
../.venv/bin/python3 main.py list --state pending
../.venv/bin/python3 main.py list --state failed
../.venv/bin/python3 main.py list --state dead

💀 Dead Letter Queue (DLQ)
../.venv/bin/python3 main.py dlq list

🔧 Configuration
../.venv/bin/python3 main.py config show
../.venv/bin/python3 main.py config set backoff-base 3


🎯 Automated Testing
./test.sh



Covers:
✔ Enqueue
✔ Worker start
✔ Retry behavior
✔ DLQ
✔ Logging


🛠️ Issues Encountered

### Issue 1 — Worker stayed idle, nothing processed
### Issue 2 — Crash: “Python quit unexpectedly”
Caused by system Python's broken SQLite build.
Fix: run everything using the venv interpreter.

### Issue 4 — SQLite error: “cannot start a transaction within a transaction”
Cause: manual BEGIN IMMEDIATE in job claiming.
Fix: replaced with atomic UPDATE ... WHERE state='pending'.



EXTENSIVELY USED CHATGPT for this project....
