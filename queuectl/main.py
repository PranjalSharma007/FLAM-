# main.py
import argparse
import sys
from job import Job, enqueue, list_jobs, get_summary, retry_dlq
from worker import start_workers
from util import uuid4_hex
from config import config_set, get_config

def cmd_enqueue(args):
    payload = args.payload
    if payload.startswith("@"):
        with open(payload[1:], "rb") as fh:
            payload_bytes = fh.read()
    else:
        payload_bytes = payload.encode()
    job = Job.from_json_bytes(payload_bytes)
    if not job.id:
        job.id = uuid4_hex()
    if not job.max_retries:
        job.max_retries = get_config().default_max_retries
    enqueue(job)
    print("enqueued", job.id)

def cmd_worker(args):
    if args.action == "start":
        start_workers(count=args.count, poll_interval=args.poll)
    else:
        print("unknown worker action")

def cmd_status(args):
    s = get_summary()
    print("pending={pending} processing={processing} completed={completed} failed={failed} dead={dead}".format(**s))

def cmd_list(args):
    rows = list_jobs(state=args.state)
    for r in rows:
        print(r["id"], r["state"], f"attempts={r['attempts']}", f"max={r['max_retries']}", r["updated_at"])

def cmd_dlq(args):
    if args.action == "list":
        rows = list_jobs(state="dead")
        for r in rows:
            print(r["id"], r["command"], "last_error=", r["last_error"])
    elif args.action == "retry":
        ok = retry_dlq(args.jobid)
        if ok:
            print("requeued", args.jobid)
        else:
            print("job not found or not in DLQ:", args.jobid)

def cmd_config(args):
    if args.action == "set":
        try:
            config_set(args.key, args.value)
            print("ok")
        except Exception as e:
            print("error:", e)
    else:
        cfg = get_config()
        print(f"backoff-base={cfg.backoff_base} default-max-retries={cfg.default_max_retries}")

def build_parser():
    p = argparse.ArgumentParser(prog="queuectl")
    sp = p.add_subparsers(dest="cmd")

    e = sp.add_parser("enqueue")
    e.add_argument("payload", help="job JSON string or @file")
    e.set_defaults(func=cmd_enqueue)

    w = sp.add_parser("worker")
    w.add_argument("action", choices=["start", "stop"], help="start or stop")
    w.add_argument("--count", type=int, default=1)
    w.add_argument("--poll", type=float, default=2.0)
    w.set_defaults(func=cmd_worker)

    s = sp.add_parser("status")
    s.set_defaults(func=cmd_status)

    l = sp.add_parser("list")
    l.add_argument("--state", default=None, help="filter by state")
    l.set_defaults(func=cmd_list)

    dlq = sp.add_parser("dlq")
    dlq.add_argument("action", choices=["list", "retry"])
    dlq.add_argument("jobid", nargs='?')
    dlq.set_defaults(func=cmd_dlq)

    cfg = sp.add_parser("config")
    cfg.add_argument("action", choices=["set", "show"])
    cfg.add_argument("key", nargs='?')
    cfg.add_argument("value", nargs='?')
    cfg.set_defaults(func=cmd_config)

    return p

def main():
    p = build_parser()
    args = p.parse_args()
    if not hasattr(args, "func"):
        p.print_help()
        sys.exit(1)
    args.func(args)

if __name__ == "__main__":
    main()
