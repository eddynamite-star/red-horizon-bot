import os
from flask import Flask, request, jsonify
from .persistence import log, clean_seen_links
from .tasks import (
    run_digest, run_breaking, run_super_priority, run_daily_image,
    run_book_spotlight, run_welcome, run_starbase_fact, SEEN_FILE
)

CRON_SECRET = os.getenv("CRON_SECRET")

app = Flask(__name__)

@app.get("/")
def index():
    from datetime import datetime, timezone
    return f"Red Horizon bot is up. UTC {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S}", 200

def _auth():
    key = request.args.get("key", "")
    return CRON_SECRET and key == CRON_SECRET

@app.get("/run")
def run_task():
    if not _auth():
        log("Unauthorized /run"); return ("Unauthorized", 401)
    task = (request.args.get("task") or "").strip().lower()
    force = (request.args.get("force") or "0").lower() in ("1","true","yes","on")
    mapping = {
        "digest": lambda: run_digest(),
        "breaking": lambda: run_breaking(),
        "priority": lambda: run_super_priority(force=force),
        "image": lambda: run_daily_image(),
        "book": lambda: run_book_spotlight(),
        "welcome": lambda: run_welcome(),
        "fact": lambda: run_starbase_fact(),
    }
    fn = mapping.get(task)
    if not fn:
        return (f"Unknown task: {task}", 400)
    log(f"/run: {task} start (force={force})")
    try:
        clean_seen_links(SEEN_FILE)
        res = fn()
        log(f"/run: {task} -> {res}")
        return jsonify({"ok": True, "task": task, "result": res})
    except Exception as e:
        log(f"/run: {task} ERROR {e}")
        return jsonify({"ok": False, "task": task, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
