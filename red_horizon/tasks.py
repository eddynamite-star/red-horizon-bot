import os, random, re, time
from datetime import datetime, timedelta
from .config import (
    HASHTAG_LINE, MAX_ITEMS, SEEN_TTL_DAYS, UTC, WELCOME_MESSAGE,
    BREAKING_MAX_AGE_MIN, ENABLE_SUPER_PRIORITY, SUPER_COOLDOWN_MIN
)
from .persistence import log, load_json, save_json
from .telegram import post_to_telegram, md_escape
from .feeds import (
    fetch_news, fetch_images, fetch_priority_candidates,
    mark_seen
)

BOOKS_FILE = "books.json"
FACTS_FILE = "starbase_facts.json"
SEEN_FILE  = "seen_links.json"
BOOK_INDEX_FILE = "book_index.json"
FACT_INDEX_FILE = "fact_index.json"
PRIORITY_STATE_FILE = "priority_state.json"

BOOKS = load_json(BOOKS_FILE, [])
FACTS = load_json(FACTS_FILE, [])
BOOK_IDX = load_json(BOOK_INDEX_FILE, {"index": 0})
FACT_IDX = load_json(FACT_INDEX_FILE, {"index": 0})
SEEN     = load_json(SEEN_FILE, {})
PR_STATE = load_json(PRIORITY_STATE_FILE, {"last_ts": 0, "last_url": ""})

BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
ZAPIER_HOOK_URL = os.getenv("ZAPIER_HOOK_URL")

def forward_tweet_to_zapier(tweet_text: str, photo_url: str=None):
    if not ZAPIER_HOOK_URL: return
    import requests
    try:
        payload = {"tweet": tweet_text}
        if photo_url: payload["photo_url"] = photo_url
        r = requests.post(ZAPIER_HOOK_URL, json=payload, timeout=10)
        if r.status_code >= 300:
            log(f"Zapier forward error {r.status_code}: {r.text}")
    except Exception as e:
        log(f"Zapier forward exception: {e}")

def make_digest(items):
    today = datetime.now(UTC).strftime("%b %d, %Y")
    lines = [f"🚀 *Red Horizon Daily Digest* — {today}\n"]
    for it in items[:MAX_ITEMS]:
        tag = "🚀"
        low = it['title'].lower()
        if any(k in low for k in ["starbase","boca chica","spacex starship"]):
            tag = "🛠"
        title = md_escape(it['title'])
        lines.append(f"• {tag} *{title}* — {it['link']}")
    lines.append("\n" + HASHTAG_LINE)
    return "\n".join(lines)[:4090]

def run_digest():
    try:
        items = fetch_news(SEEN, SEEN_FILE, SEEN_TTL_DAYS)
        if not items:
            log("run_digest: no items"); return "no_items"
        msg = make_digest(items)
        post_to_telegram(BOT_TOKEN, CHANNEL_ID, msg)
        for it in items[:MAX_ITEMS]:
            mark_seen(it["link"], SEEN, SEEN_FILE)
        tweet = f"🚀 Red Horizon Daily Digest — {datetime.now(UTC).strftime('%b %d')}\nSpaceX, NASA & Mars updates.\n👉 Full digest: t.me/RedHorizonHub\n\n#SpaceX #Mars #RedHorizon"
        forward_tweet_to_zapier(tweet)
        return "ok"
    except Exception as e:
        log(f"run_digest error: {e}"); return "error"

def run_breaking():
    try:
        items = fetch_news(SEEN, SEEN_FILE, SEEN_TTL_DAYS)
        if not items:
            log("run_breaking: no items"); return "no_items"

        now = datetime.now(UTC)
        fresh = [it for it in items if (now - it["published"]).total_seconds() <= BREAKING_MAX_AGE_MIN*60]
        if not fresh:
            log("run_breaking: no fresh within window"); return "no_fresh"

        spacex_first = [it for it in fresh if re.search(r"\b(spacex|starship|starbase|falcon|super heavy|booster|raptor|starlink)\b", it["title"], re.I)]
        def sortkey(x): return (x.get("score", 0.0), x["published"])
        pick = sorted(spacex_first or fresh, key=sortkey, reverse=True)[0]

        title = md_escape(pick['title'])
        text = f"🚨 *Breaking News* — {title}\n{pick['link']}\n\n#SpaceX #Starship #RedHorizon"
        post_to_telegram(BOT_TOKEN, CHANNEL_ID, text, buttons=[("Read Source", pick["link"])])
        mark_seen(pick["link"], SEEN, SEEN_FILE)

        tweet = f"🚨 Breaking: {pick['title']}\n👉 Details → t.me/RedHorizonHub\n\n#SpaceX #Starship #RedHorizon"
        forward_tweet_to_zapier(tweet)
        return "ok"
    except Exception as e:
        log(f"run_breaking error: {e}"); return "error"

def run_super_priority(force=False):
    try:
        if not ENABLE_SUPER_PRIORITY and not force:
            return "disabled"
        now = time.time()
        # Cooldown
        if (not force) and (now - PR_STATE.get("last_ts", 0) < SUPER_COOLDOWN_MIN*60):
            return "cooldown"

        cands = fetch_priority_candidates(SEEN, SEEN_TTL_DAYS)
        if not cands:
            return "no_candidates"

        # Only consider within BREAKING_MAX_AGE_MIN window
        utcnow = datetime.now(UTC)
        window = [c for c in cands if (utcnow - c["published"]).total_seconds() <= BREAKING_MAX_AGE_MIN*60]
        if not window:
            return "no_fresh"

        # Prefer SpaceX/Starship terms
        spacexy = [c for c in window if re.search(r"\b(spacex|starship|starbase|falcon|super heavy|booster|raptor|starlink)\b", c["title"], re.I)]
        def sortkey(x): return (x.get("score", 0.0), x["published"])
        pick = sorted(spacexy or window, key=sortkey, reverse=True)[0]

        low = pick["title"].lower()
        if re.search(r"\b(live|livestream|streaming now|is live)\b", low):
            prefix = "🟢 LIVE NOW — "
        elif re.search(r"\b(upcoming|premiere|scheduled)\b", low):
            prefix = "🔴 LIVE SOON — "
        elif re.search(r"\b(static fire|hotfire|wdr|wet dress|stack|destack|rollback)\b", low):
            prefix = "🛠 Test Update — "
        else:
            prefix = "🚨 Priority — "

        title = md_escape(pick["title"])
        text = f"{prefix}{title}\n{pick['link']}\n\n#SpaceX #Starship #RedHorizon"
        post_to_telegram(BOT_TOKEN, CHANNEL_ID, text, buttons=[("Open", pick["link"])])

        mark_seen(pick["link"], SEEN, SEEN_FILE)
        PR_STATE["last_ts"] = now
        PR_STATE["last_url"] = pick["link"]
        save_json(PRIORITY_STATE_FILE, PR_STATE)

        # Tweet LIVE NOW and Test Update; skip LIVE SOON if you want
        if prefix.startswith("🟢") or prefix.startswith("🛠") or prefix.startswith("🚨"):
            tweet = f"{prefix}{pick['title']}\n▶️ Watch/Details → t.me/RedHorizonHub\n\n#SpaceX #Starship #RedHorizon"
            forward_tweet_to_zapier(tweet)
        return "ok"
    except Exception as e:
        log(f"run_super_priority error: {e}"); return "error"

def run_daily_image():
    try:
        cands = fetch_images(SEEN, SEEN_FILE, SEEN_TTL_DAYS)
        if not cands:
            log("run_daily_image: no candidates"); return "no_items"
        chosen = random.choice(cands[:8])
        source_tag = "📸 Space Image"
        if "flickr.com" in chosen["link"]:
            if "154560776@N07" in chosen["link"]: source_tag = "🛫 RGV Starbase Photo"
            elif "182367180@N05" in chosen["link"]: source_tag = "🌌 Andrew McCarthy Photo"
        title = md_escape(chosen['title'])
        caption = f"{source_tag}\n*{title}*\n{chosen['link']}\n\n#Astronomy #SpaceX #RedHorizon"
        post_to_telegram(BOT_TOKEN, CHANNEL_ID, caption, photo_url=chosen["img"], buttons=[("View Source", chosen["link"])])
        mark_seen(chosen["link"], SEEN, SEEN_FILE)
        tweet = f"📸 Today’s Space Image: {chosen['title']}\n🌌 More daily images: t.me/RedHorizonHub\n\n#Astronomy #NASA #RedHorizon"
        forward_tweet_to_zapier(tweet, photo_url=chosen["img"])
        return "ok"
    except Exception as e:
        log(f"run_daily_image error: {e}"); return "error"

def run_book_spotlight():
    try:
        if not BOOKS:
            log("run_book_spotlight: no books.json"); return "no_books"
        idx = BOOK_IDX.get("index", 0) % len(BOOKS)
        book = BOOKS[idx]
        title = md_escape(book['title'])
        msg = (f"📖 *Red Horizon Book Spotlight*\n"
               f"{title}\n{book['blurb']}\n\n"
               f"🔗 [Get it here]({book['link']})\n\n"
               "#Mars #SciFi #RedHorizonReads")
        post_to_telegram(BOT_TOKEN, CHANNEL_ID, msg, buttons=[("Open on Amazon", book["link"])])
        BOOK_IDX["index"] = (idx + 1) % len(BOOKS)
        save_json(BOOK_INDEX_FILE, BOOK_IDX)
        return "ok"
    except Exception as e:
        log(f"run_book_spotlight error: {e}"); return "error"

def run_welcome():
    try:
        post_to_telegram(BOT_TOKEN, CHANNEL_ID, WELCOME_MESSAGE)
        return "ok"
    except Exception as e:
        log(f"run_welcome error: {e}"); return "error"

def run_starbase_fact():
    try:
        if not FACTS:
            log("run_starbase_fact: no starbase_facts.json"); return "no_facts"
        idx = FACT_IDX.get("index", 0) % len(FACTS)
        fact = FACTS[idx]
        caption = (f"🏗 *Starbase Highlight*\n"
                   f"{md_escape(fact['title'])}\n{fact['desc']}\n\n"
                   "#Starbase #SpaceX #RedHorizon")
        buttons = [("Learn More", fact["link"])] if fact.get("link") else None
        photo = fact.get("img")
        post_to_telegram(BOT_TOKEN, CHANNEL_ID, caption, photo_url=photo, buttons=buttons)
        FACT_IDX["index"] = (idx + 1) % len(FACTS)
        save_json(FACT_INDEX_FILE, FACT_IDX)
        return "ok"
    except Exception as e:
        log(f"run_starbase_fact error: {e}"); return "error"
