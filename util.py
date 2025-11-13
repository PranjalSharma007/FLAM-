# util.py
import uuid
from datetime import datetime

def uuid4_hex():
    return uuid.uuid4().hex

def now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

