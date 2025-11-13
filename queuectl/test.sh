#!/bin/zsh
set -euo pipefail

PY=python3
WORKER_LOG=worker.log
DB_FILE=queue.db

echo
echo "=== test.sh — smoke test for queuectl ==="
echo

# cleanup previous run
if [ -f "$DB_FILE" ]; then
  echo "removing existing $DB_FILE"
  rm -f "$DB_FILE"
fi
rm -f "$WORKER_LOG" || true

# cleanup background worker on exit
cleanup() {
  if [ -n "${WPID:-}" ] && ps -p "$WPID" >/dev/null 2>&1; then
    echo "stopping worker (pid $WPID)..."
    kill "$WPID" || true
    wait "$WPID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "1) Enqueue a successful job"
$PY main.py enqueue '{"id":"job_success","command":"echo hello; sleep 1","max_retries":2}'

echo "2) Enqueue a failing job"
$PY main.py enqueue '{"id":"job_fail","command":"sh -c \"exit 2\"","max_retries":2}'

echo "3) Start workers (2 threads) in background; logs -> $WORKER_LOG"
$PY main.py worker start --count 2 --poll 1 > "$WORKER_LOG" 2>&1 &
WPID=$!
echo "worker pid: $WPID"
sleep 2

echo
echo "4) Initial status:"
$PY main.py status
echo

echo "5) Let workers run for 10 seconds..."
sleep 10

echo
echo "6) Status after processing:"
$PY main.py status
echo

echo "7) Stopping worker..."
cleanup
sleep 1

echo
echo "8) DLQ list:"
$PY main.py dlq list || true
echo

echo "9) Worker log (last 200 lines):"
if [ -f "$WORKER_LOG" ]; then
  tail -n 200 "$WORKER_LOG" || true
else
  echo "no worker log found"
fi

echo
echo "=== test complete ==="

