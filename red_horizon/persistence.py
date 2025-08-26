import os, json, time
from .config import SEEN_TTL_DAYS

LOG_DIR = ".logs"
LOG_FILE = os.path.join(LOG_DIR, "log.txt")

def _ensure_dirs():
    os.makedirs(LOG_DIR, exist_ok=True)

def _rotate_if_large(path, max_bytes=2_000_000):
    try:
        if os.path.exists(path) and os.path.getsize(path) > max_bytes:
            with open(path, "rb") as f:
                tail = f.read()[-200_000:]
            with open(path, "wb") as f:
                f.write(tail)
    except Exception:
        pass

def log(msg: str):
    _ensure_dirs()
    _rotate_if_large(LOG_FILE)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        print("LOG_FAIL:", msg)

def load_json(path: str, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log(f"load_json error {path}: {e}")
    return default

def save_json(path: str, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        log(f"save_json error {path}: {e}")

def clean_seen_links(path: str):
    """Prune entries older than TTL to keep file tiny."""
    try:
        now = time.time()
        ttl = SEEN_TTL_DAYS * 86400
        d = load_json(path, {})
        if not isinstance(d, dict): d = {}
        pruned = {k:v for k,v in d.items() if isinstance(v,(int,float)) and (now - v) <= ttl}
        if len(pruned) != len(d):
            save_json(path, pruned)
            log(f"clean_seen_links: pruned {len(d)-len(pruned)}")
    except Exception as e:
        log(f"clean_seen_links error: {e}")
