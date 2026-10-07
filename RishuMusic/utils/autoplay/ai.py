# ============================================================
# RishuMusic/utils/autoplay/ai.py — v1  (NEW FILE)
#
# AI picks 5 songs related to the one that is playing. It only returns NAMES
# ("Song - Artist"); related.py then searches each name on YouTube and the
# normal prefetch downloads them (YouTube.download = your API + fallback).
# So the AI can never break playback: if every AI provider fails, related.py
# silently uses the old method (YouTube search + YouTube Mix).
#
# Providers are tried in this order (a provider with no key is skipped):
#   1) Gemini   - env GEMINI_API_KEY   (free key: aistudio.google.com)
#   2) Groq     - env GROQ_API_KEY     (free key: console.groq.com)
#   3) Pollinations - no key needed (anonymous, rate limited, least stable)
# A provider that fails (HTTP error / 429 / timeout) is benched for 90 s, so a
# dead or rate-limited provider never slows the next songs down.
#
# Optional env:  GEMINI_MODEL (default gemini-2.5-flash-lite)
#                GROQ_MODELS  (comma list, default llama-3.1-8b-instant,openai/gpt-oss-20b)
#                POLLINATIONS_KEY, AI_AUTOPLAY=0 (turn the AI part off)
# Free-tier models/limits change often - if one is retired just change the env var.
# ============================================================

import asyncio
import json
import os
import re
import time
from urllib.parse import quote

import aiohttp

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite").strip()
GEMINI_URL = os.environ.get(
    "GEMINI_URL", "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_MODELS = [
    m.strip()
    for m in os.environ.get("GROQ_MODELS", "llama-3.1-8b-instant,openai/gpt-oss-20b").split(",")
    if m.strip()
]
GROQ_URL = os.environ.get("GROQ_URL", "https://api.groq.com/openai/v1/chat/completions")
POLL_KEY = os.environ.get("POLLINATIONS_KEY", "").strip()
POLL_URL = os.environ.get("POLLINATIONS_URL", "https://gen.pollinations.ai/text/")
ENABLED = os.environ.get("AI_AUTOPLAY", "1") != "0"

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
