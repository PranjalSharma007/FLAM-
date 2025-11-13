# worker.py
import threading
import subprocess
import time
import signal
import sys
from job import claim_next_pending, mark_completed, mark_failed_with_retry, move_to_dead
from config import get_config
from util import now_iso

_stop_event = threading.Event()

def _handle_signal(sig, frame):
    print("signal received, stopping workers gracefully...")
    _stop_event.set()

signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

def start_workers(count: int = 1, poll_interval: float = 2.0):
    threads = []
    for i in range(count):
        t = threading.Thread(target=worker_loop, args=(f"worker-{i}", poll_interval), daemon=True)
        threads.append(t)
        t.start()
    print(f"started {count} workers (threads). press Ctrl-C to stop.")
    try:
        while not _stop_event.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        _stop_event.set()
    for t in threads:
        t.join()
    print("all workers stopped")

def worker_loop(worker_id: str, poll_interval: float):
    cfg = get_config()
    while not _stop_event.is_set():
        job = claim_next_pending(worker_id)
        if not job:
            time.sleep(poll_interval)
            continue
        job_id = job["id"]
        cmd = job["command"]
        attempts = job["attempts"]
        max_retry = job["max_retries"]
        print(f"{worker_id} picked job {job_id} cmd='{cmd}' attempts={attempts} max_retries={max_retry}")
        # execute command (shell)
        try:
            completed = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=None)
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            exit_code = completed.returncode
        except Exception as ex:
            exit_code = 1
            stdout = ""
            stderr = str(ex)

        if exit_code == 0:
            combined = (stdout + stderr).strip()
            mark_completed(job_id, combined)
            print(f"{worker_id} job {job_id} completed")
            continue

        # failed
        attempts = attempts + 1
        if attempts > max_retry:
            move_to_dead(job_id, stderr or "failed")
            print(f"{worker_id} job {job_id} moved to DLQ after {attempts-1} attempts")
            continue

        # exponential backoff: delay = base ** attempts (seconds)
        base = cfg.backoff_base or 2
        delay = (base ** attempts)
        next_retry_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + delay))
        mark_failed_with_retry(job_id, attempts, stderr, next_retry_at)
        print(f"{worker_id} job {job_id} failed (attempt {attempts}). next retry at {next_retry_at}")


