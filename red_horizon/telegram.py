import requests, time, re
from .persistence import log

_MD_RE = re.compile(r'([_*()\[\]])')  # basic Markdown escape for Telegram

def md_escape(s: str) -> str:
    if not s: return s
    return _MD_RE.sub(r'\\\1', s)

def tg_request(bot_token: str, method: str, payload: dict):
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    for attempt in range(3):
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", "2"))
            time.sleep(min(wait, 10)); continue
        if r.status_code >= 500:
            time.sleep(2*(attempt+1)); continue
        return r
    log(f"tg_request failed {method}: {getattr(r,'status_code','no_resp')}")
    return r

def split_chunks(text: str, limit=4096):
    if len(text) <= limit: return [text]
    parts, cur = [], []
    for line in text.split("\n"):
        if sum(len(x)+1 for x in cur) + len(line) + 1 > limit:
            parts.append("\n".join(cur)); cur=[line]
        else:
            cur.append(line)
    if cur: parts.append("\n".join(cur))
    return parts

def post_to_telegram(bot_token: str, chat_id: str, text: str, photo_url: str=None, buttons=None):
    reply_markup = None
    if buttons:
        reply_markup = {"inline_keyboard": [[{"text": t, "url": u}] for (t,u) in buttons]}

    if photo_url:
        payload = {"chat_id": chat_id, "photo": photo_url, "caption": text, "parse_mode": "Markdown"}
        if reply_markup: payload["reply_markup"] = reply_markup
        r = tg_request(bot_token, "sendPhoto", payload)
        if r is not None and r.status_code >= 300:
            log(f"sendPhoto error {r.status_code}: {r.text}")
        return

    for chunk in split_chunks(text):
        payload = {"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown", "disable_web_page_preview": False}
        if reply_markup: payload["reply_markup"] = reply_markup
        r = tg_request(bot_token, "sendMessage", payload)
        if r is not None and r.status_code >= 300:
            log(f"sendMessage error {r.status_code}: {r.text}")
