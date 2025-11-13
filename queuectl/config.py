# config.py
class Config:
    def __init__(self):
        self.backoff_base = 2
        self.default_max_retries = 3

_cfg = Config()

def get_config():
    return _cfg

def config_set(key: str, value: str):
    if key in ("backoff-base", "backoff_base"):
        _cfg.backoff_base = int(value)
    elif key in ("default-max-retries", "max-retries", "default_max_retries"):
        _cfg.default_max_retries = int(value)
    else:
        raise KeyError(f"unknown config key {key}")
