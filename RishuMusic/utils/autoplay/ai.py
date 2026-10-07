# ============================================================
# RishuMusic/utils/autoplay/ai.py — v2
#
# AI picks 5 songs related to the one that is playing. It only returns NAMES
# ("Song - Artist"); related.py then searches each name on YouTube and the
# normal prefetch downloads them (YouTube.download = your API + fallback).
# So the AI can never break playback: if every AI provider fails, related.py
# silently uses the old method (YouTube search + YouTube Mix).
#
# v2: keys/settings are now imported from config.py (fallback: os.environ).
#     config.py me ye add kar do (sab optional):
#         GEMINI_API_KEY   = getenv("GEMINI_API_KEY", "")
#         GEMINI_MODEL     = getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
#         GROQ_API_KEY     = getenv("GROQ_API_KEY", "")
#         GROQ_MODELS      = getenv("GROQ_MODELS", "llama-3.1-8b-instant,openai/gpt-oss-20b")
#         POLLINATIONS_KEY = getenv("POLLINATIONS_KEY", "")
#         AI_AUTOPLAY      = getenv("AI_AUTOPLAY", "1")
#
# Providers order (provider with no key is skipped):
#   1) Gemini  2) Groq  3) Pollinations (no key needed)
# A failing provider is benched for 90 s.
# ============================================================

import asyncio
import json
import os
import re
import time
from urllib.parse import quote

import aiohttp

try:
    import config as _config
except Exception:  # config missing / broken -> fall back to env only
    _config = None


def _cfg(name: str, default: str = "") -> str:
    """config.py value first, then environment, then default."""
    val = getattr(_config, name, None) if _config else None
    if val is None or str(val).strip() == "":
        val = os.environ.get(name, default)
    return str(val).strip()


GEMINI_KEY = _cfg("GEMINI_API_KEY")
GEMINI_MODEL = _cfg("GEMINI_MODEL", "gemini-2.5-flash-lite")
GEMINI_URL = _cfg(
    "GEMINI_URL", "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
GROQ_KEY = _cfg("GROQ_API_KEY")
GROQ_MODELS = [
    m.strip()
    for m in _cfg("GROQ_MODELS", "llama-3.1-8b-instant,openai/gpt-oss-20b").split(",")
    if m.strip()
]
GROQ_URL = _cfg("GROQ_URL", "https://api.groq.com/openai/v1/chat/completions")
POLL_KEY = _cfg("POLLINATIONS_KEY")
POLL_URL = _cfg("POLLINATIONS_URL", "https://gen.pollinations.ai/text/")
ENABLED = _cfg("AI_AUTOPLAY", "1") != "0"

COUNT = 5
TIMEOUT = 12  # seconds per provider
BENCH_SECONDS = 90
CACHE_SECONDS = 3600

_bench_until = {}  # provider -> unix time
_cache = {}  # normalised title -> (time, names)
_sem = asyncio.Semaphore(2)  # never hammer the free APIs


def _prompt(title: str) -> str:
    return (
        f'The song playing now is: "{title}".\n'
        f"Suggest exactly {COUNT} OTHER real, popular songs this listener would enjoy next "
        "(same language, mood, era or similar artists). "
        'Reply with ONLY a JSON array of strings, each formatted "Song Title - Artist". '
        "No explanations, no numbering, no markdown."
    )


def parse_names(text, limit: int = COUNT + 3):
    """Pull song names out of whatever the model returned (JSON array, fenced JSON or plain lines)."""
    if not text:
        return []
    t = re.sub(r"```(?:json)?", "", str(text)).strip()
    items = None
    m = re.search(r"\[.*\]", t, re.S)
    if m:
        try:
            arr = json.loads(m.group(0))
            items = [str(x) for x in arr if isinstance(x, (str, int, float))]
        except Exception:
            items = None
    if items is None:
        # plain lines: only bullet / numbered lines or "Song - Artist" lines count, so a refusal
        # like "Sorry, I can't help" is never searched as if it were a song name
        items = []
        for ln in t.splitlines():
            listed = re.match(r"^\s*(?:[-*•]|\d+[.)])\s+", ln)
            if listed or " - " in ln:
                items.append(re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", ln))
    out, seen = [], set()
    for x in items:
        x = re.sub(r"\s+", " ", str(x)).strip(" \"'`,[]")
        if 3 <= len(x) <= 120 and x.lower() not in seen:
            seen.add(x.lower())
            out.append(x)
    return out[:limit]


# ---------------- providers ----------------
async def _gemini(sess, prompt):
    url = GEMINI_URL.format(model=GEMINI_MODEL)
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 800},
    }
    async with sess.post(url, headers={"x-goog-api-key": GEMINI_KEY}, json=body) as r:
        if r.status != 200:
            raise RuntimeError(f"gemini HTTP {r.status}")
        j = await r.json(content_type=None)
    return "".join(p.get("text", "") for p in j["candidates"][0]["content"]["parts"])


async def _groq(sess, prompt):
    last = None
    for model in GROQ_MODELS:
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 400,
        }
        async with sess.post(GROQ_URL, headers={"Authorization": f"Bearer {GROQ_KEY}"}, json=body) as r:
            if r.status == 200:
                j = await r.json(content_type=None)
                return j["choices"][0]["message"]["content"]
            last = r.status
            if r.status in (401, 403, 429):  # key / rate problem: another model won't help
                break
    raise RuntimeError(f"groq HTTP {last}")


async def _pollinations(sess, prompt):
    params = {"key": POLL_KEY} if POLL_KEY else None
    # the prompt travels inside the URL path: no newlines / slashes (they break path routing)
    flat = re.sub(r"\s+", " ", prompt).replace("/", "-")
    async with sess.get(POLL_URL + quote(flat, safe=""), params=params) as r:
        if r.status != 200:
            raise RuntimeError(f"pollinations HTTP {r.status}")
        return await r.text()


def _providers():
    p = []
    if GEMINI_KEY:
        p.append(("gemini", _gemini))
    if GROQ_KEY:
        p.append(("groq", _groq))
    p.append(("pollinations", _pollinations))
    return p


async def ai_related(title: str):
    """Up to 5 'Song - Artist' names related to `title`. [] if AI is off or everything failed."""
    if not ENABLED or not title:
        return []
    key = re.sub(r"[^a-z0-9]", "", title.lower())
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return list(hit[1])

    prompt = _prompt(title)
    async with _sem:
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            for name, fn in _providers():
                if _bench_until.get(name, 0) > time.time():
                    continue
                try:
                    names = parse_names(await fn(sess, prompt))
                except asyncio.CancelledError:
                    raise
                except Exception:
                    _bench_until[name] = time.time() + BENCH_SECONDS
                    continue
                if names:
                    if len(_cache) > 300:
                        _cache.clear()
                    _cache[key] = (time.time(), names)
                    return names
    return []
