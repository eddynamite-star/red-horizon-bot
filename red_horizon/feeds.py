import re, random, time, requests, feedparser
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse
from difflib import SequenceMatcher

from .config import (
    FEEDS, IMAGE_FEEDS, KEYWORDS, STARBASE_KEYWORDS, PRIORITY_KEYWORDS,
    NEGATIVE_HINTS, PROVIDER_WEIGHTS, HIGH_SIGNAL_DOMAINS, YOUTUBE_FEEDS,
    FRESHNESS_DAYS, UTC, BREAKING_MIN_SCORE
)
from .persistence import log, save_json

UA = {"User-Agent": "RedHorizonBot/1.0 (+https://t.me/RedHorizonHub)"}

_DOMAIN_RE = re.compile(r"https?://([^/]+)/", re.I)

def get_domain(url: str):
    m = _DOMAIN_RE.match(url or "")
    return (m.group(1).lower() if m else "").replace("www.", "")

def fetch_feed(url: str):
    try:
        r = requests.get(url, headers=UA, timeout=10)
        r.raise_for_status()
        return feedparser.parse(r.content)
    except Exception as e:
        log(f"fetch_feed error {url}: {e}")
        return feedparser.parse(b"")

def canonical_url(u: str):
    try:
        p = urlparse(u)
        return urlunparse(p._replace(query="", fragment=""))
    except Exception:
        return u

def is_english(text: str):
    if not text: return False
    non_ascii = sum(1 for c in text if ord(c) > 127)
    return non_ascii < len(text) * 0.1

def is_recent(entry):
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            pub = datetime(*entry.published_parsed[:6], tzinfo=UTC)
            return pub > datetime.now(UTC) - timedelta(days=FRESHNESS_DAYS)
    except Exception:
        pass
    return True

def is_relevant(text: str):
    return any(re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE) for kw in KEYWORDS)

def text_hits_any(text: str, words):
    if not text: return 0
    t = text.lower()
    hits = 0
    for w in words:
        if re.search(rf"\b{re.escape(w)}\b", t):
            hits += 1
    return hits

def relevance_score(title: str, summary: str, link: str):
    """Score by keyword hits + provider weight + priority terms - negatives."""
    t = (title or "").lower()
    s = (summary or "").lower()
    domain = get_domain(link)
    score = 0.0
    score += 1.5 * text_hits_any(t, KEYWORDS)
    score += 0.5 * text_hits_any(s, KEYWORDS)
    score += 1.5 * text_hits_any(t, PRIORITY_KEYWORDS)
    score += 0.75 * text_hits_any(s, PRIORITY_KEYWORDS)
    score += PROVIDER_WEIGHTS.get(domain, 0.0)
    if text_hits_any(t, NEGATIVE_HINTS) or text_hits_any(s, NEGATIVE_HINTS):
        score -= 1.0
    return score

def fuzzy_dedupe(items, threshold=0.90):
    kept, norms = [], []
    def norm(t):
        t = t.lower()
        t = re.sub(r"[^a-z0-9 ]+", " ", t)
        return re.sub(r"\s+"," ", t).strip()
    for it in items:
        n = norm(it["title"])
        if any(SequenceMatcher(None, n, s).ratio() >= threshold for s in norms):
            continue
        kept.append(it); norms.append(n)
    return kept

def extract_image_from_entry(e):
    try:
        if "enclosures" in e and e.enclosures:
            url = e.enclosures[0].get("url")
            if url: return url
        if "media_content" in e and e.media_content:
            url = e.media_content[0].get("url")
            if url: return url
        desc = e.get("description") or e.get("summary") or ""
        m = re.search(r'<img[^>]+src="([^"]+)"', desc)
        return m.group(1) if m else None
    except Exception:
        return None

def _not_recently_seen(url: str, seen: dict, ttl_days: int):
    now = time.time()
    then = seen.get(url)
    return (then is None) or (now - then) > ttl_days*86400

def _mark_seen(url: str, seen: dict, seen_path: str):
    seen[url] = time.time()
    save_json(seen_path, seen)

def fetch_news(seen: dict, seen_path: str, ttl_days: int):
    items=[]
    for url in set(FEEDS):
        feed = fetch_feed(url)
        for e in feed.entries[:6]:
            title = (e.get("title") or "").strip()
            link  = canonical_url((e.get("link") or "").strip())
            if not title or not link: continue
            summary = (e.get("summary") or e.get("description") or "").strip()
            if not is_english(title): continue
            if not is_recent(e): continue
            if not (is_relevant(title) or (summary and is_relevant(summary))): continue
            score = relevance_score(title, summary, link)
            if score < BREAKING_MIN_SCORE: continue
            pub = datetime(*e.published_parsed[:6], tzinfo=UTC) if e.get("published_parsed") else datetime.now(UTC)
            if _not_recently_seen(link, seen, ttl_days):
                items.append({"title":title, "link":link, "published":pub, "score":score})

    newest={}
    for it in items:
        prev = newest.get(it["title"])
        if (not prev) or (it["published"] > prev["published"]) or (it["score"] > prev["score"]):
            newest[it["title"]] = it

    dedup = fuzzy_dedupe(list(newest.values()))
    dedup.sort(key=lambda x: (x["score"], x["published"]), reverse=True)
    return dedup

def fetch_images(seen: dict, seen_path: str, ttl_days: int):
    cands=[]
    for url in set(IMAGE_FEEDS):
        feed = fetch_feed(url)
        for e in feed.entries[:6]:
            title=(e.get("title") or "").strip()
            link = canonical_url((e.get("link") or "").strip())
            if not title or not link: continue
            if not is_recent(e): continue
            desc = (e.get("description") or e.get("summary") or "")
            if not (is_relevant(title) or (desc and is_relevant(desc))): continue
            img = extract_image_from_entry(e)
            if not img: continue
            if _not_recently_seen(link, seen, ttl_days):
                cands.append({"title":title,"link":link,"img":img})
    random.shuffle(cands)
    return cands

def fetch_priority_candidates(seen: dict, ttl_days: int):
    """Super-priority signals from YouTube feeds and high-signal domains."""
    items=[]
    # YouTube signals
    for url in YOUTUBE_FEEDS:
        feed = fetch_feed(url)
        for e in feed.entries[:5]:
            title = (e.get("title") or "").strip()
            link  = canonical_url((e.get("link") or "").strip())
            if not title or not link: continue
            # Must be English-ish title
            if not is_english(title): continue
            # Look for LIVE / UPCOMING / priority terms + SpaceX context preferred
            low = title.lower()
            if not any(k in low for k in [*PRIORITY_KEYWORDS, "live","stream","premiere","upcoming"]):
                continue
            # score it
            score = relevance_score(title, "", link)
            pub = datetime(*e.published_parsed[:6], tzinfo=UTC) if e.get("published_parsed") else datetime.now(UTC)
            items.append({"title":title,"link":link,"published":pub,"score":score})

    # High-signal website feeds for priority words
    for url in set(FEEDS):
        if not any(d in url for d in HIGH_SIGNAL_DOMAINS): continue
        feed = fetch_feed(url)
        for e in feed.entries[:5]:
            title = (e.get("title") or "").strip()
            link  = canonical_url((e.get("link") or "").strip())
            if not title or not link: continue
            if not is_english(title): continue
            low = title.lower()
            if not any(k in low for k in PRIORITY_KEYWORDS): continue
            score = relevance_score(title, "", link)
            pub = datetime(*e.published_parsed[:6], tzinfo=UTC) if e.get("published_parsed") else datetime.now(UTC)
            items.append({"title":title,"link":link,"published":pub,"score":score})

    if not items: return []
    items.sort(key=lambda x: (x["score"], x["published"]), reverse=True)
    return items

# expose helpers
not_recently_seen = _not_recently_seen
mark_seen = _mark_seen
