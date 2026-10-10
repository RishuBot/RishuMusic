# ============================================================
# RishuMusic/utils/autoplay/ai.py — v5
#   v5 (after the Owner DM "gemini HTTP 404 | groq: empty answer | pollinations HTTP 401"):
#     - Gemini: gemini-2.5-flash-lite was retired -> tries gemini-flash-lite-latest (alias that never
#       retires), gemini-3.5-flash-lite, gemini-3.1-flash-lite, gemini-flash-latest; a 404 model is
#       skipped for 6 h, and if all fail it asks Google's own model list.
#     - Groq: tries llama-3.1-8b-instant, llama-3.3-70b-versatile, gpt-oss-20b (low reasoning);
#       an EMPTY answer now moves on to the next model; falls back to Groq's own model list.
#     - Pollinations now needs a key (HTTP 401) -> only used when POLLINATIONS_KEY is set.
#     - Error text from the API is kept, so the Owner DM shows the real reason.
#   (v4 line follows)
# RishuMusic/utils/autoplay/ai.py — v4   (v4: avoid-list of recently played songs in the prompt + cache key,
#   asks for 8 names, LAST = why AI worked / failed)
# (v3 = 8 s cap)   (v3: whole AI step capped at 8 s, 6 s per provider)
# (v2 = config.py settings)
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
GEMINI_URL = _cfg(
    "GEMINI_URL", "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
GEMINI_LIST_URL = _cfg("GEMINI_LIST_URL", "https://generativelanguage.googleapis.com/v1beta/models")
# your own GEMINI_MODEL (if set) goes first; the rest are current as of Oct 2026
GEMINI_MODELS = [m for m in dict.fromkeys(
    [_cfg("GEMINI_MODEL")]
    + ["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-latest"]
) if m]
GROQ_KEY = _cfg("GROQ_API_KEY")
GROQ_MODELS = [m for m in dict.fromkeys(
    [x.strip() for x in _cfg("GROQ_MODELS").split(",")]
    + ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "openai/gpt-oss-20b"]
) if m]
GROQ_URL = _cfg("GROQ_URL", "https://api.groq.com/openai/v1/chat/completions")
GROQ_LIST_URL = _cfg("GROQ_LIST_URL", "https://api.groq.com/openai/v1/models")
POLL_KEY = _cfg("POLLINATIONS_KEY")
POLL_URL = _cfg("POLLINATIONS_URL", "https://gen.pollinations.ai/text/")
ENABLED = _cfg("AI_AUTOPLAY", "1").lower() not in ("0", "false", "no", "off")

COUNT = 5
TIMEOUT = 6  # seconds per provider
DEADLINE = 8  # seconds for the WHOLE AI step (never holds autoplay back longer)
BENCH_SECONDS = 90
CACHE_SECONDS = 3600

_bench_until = {}  # provider -> unix time
_cache = {}  # normalised title -> (time, names)
_sem = asyncio.Semaphore(2)  # never hammer the free APIs


def _prompt(title: str, avoid=None) -> str:
    skip = ""
    if avoid:
        skip = (
            "Do NOT suggest any of these (already played in this chat): "
            + "; ".join(str(a)[:80] for a in list(avoid)[-10:])
            + ".\n"
        )
    return (
        f'The song playing now is: "{title}".\n'
        f"{skip}"
        f"Suggest exactly {COUNT + 3} OTHER real, popular songs this listener would enjoy next "
        "(same language, mood, era or similar artists). Mix a few different artists, not only one. "
        'Reply with ONLY a JSON array of strings, each formatted "Song Title - Artist". '
        "No explanations, no numbering, no markdown."
    )


# v4: what happened on the last call - read by prefetch.py to tell the Owner whether AI really works
LAST = {"ok": None, "provider": "", "why": ""}


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
_dead_models = {}  # model -> time until which it is skipped (retired / not found)
DEAD_SECONDS = 6 * 3600
_NOT_CHAT = re.compile(r"whisper|tts|guard|orpheus|playai|safeguard|embed|image|imagen|live|audio|robotics|computer", re.I)


async def _err(r, who):
    """Exception text with the API's own message (shown in the Owner DM)."""
    try:
        body = re.sub(r"\s+", " ", (await r.text()))[:110]
    except Exception:
        body = ""
    return RuntimeError(f"{who} HTTP {r.status} {body}".strip())


def _alive(model):
    return _dead_models.get(model, 0) < time.time()


async def _gemini_call(sess, model, prompt):
    url = GEMINI_URL.format(model=model)
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 800},
    }
    async with sess.post(url, headers={"x-goog-api-key": GEMINI_KEY}, json=body) as r:
        if r.status != 200:
            raise await _err(r, f"gemini[{model}]")
        j = await r.json(content_type=None)
    return "".join(p.get("text", "") for p in j["candidates"][0]["content"]["parts"])


async def _gemini_discover(sess):
    """Ask Google which models this key can use (flash-lite first, newest version first)."""
    async with sess.get(GEMINI_LIST_URL, headers={"x-goog-api-key": GEMINI_KEY}, params={"pageSize": 200}) as r:
        if r.status != 200:
            raise await _err(r, "gemini-list")
        j = await r.json(content_type=None)
    out = []
    for m in j.get("models", []):
        name = str(m.get("name", "")).replace("models/", "")
        if "generateContent" not in (m.get("supportedGenerationMethods") or []):
            continue
        if "flash" not in name or _NOT_CHAT.search(name) or "preview" in name or "exp" in name:
            continue
        ver = re.search(r"(\d+(?:\.\d+)?)", name)
        out.append((0 if "lite" in name else 1, -float(ver.group(1)) if ver else 0, name))
    return [n for _a, _b, n in sorted(out)][:3]


async def _gemini(sess, prompt):
    last = None
    for model in GEMINI_MODELS:
        if not _alive(model):
            continue
        try:
            text = await _gemini_call(sess, model, prompt)
        except RuntimeError as ex:
            last = ex
            if " HTTP 404" in str(ex) or " HTTP 400" in str(ex):  # retired / unknown model: skip it for a while
                _dead_models[model] = time.time() + DEAD_SECONDS
                continue
            raise  # 401/403/429/5xx: the key or the service, another model will not help
        if text.strip():
            return text
        last = RuntimeError(f"gemini[{model}] empty answer")
    # every listed model is gone -> use whatever Google says is available now
    for model in await _gemini_discover(sess):
        if not _alive(model):
            continue
        try:
            text = await _gemini_call(sess, model, prompt)
        except RuntimeError as ex:
            last = ex
            _dead_models[model] = time.time() + DEAD_SECONDS
            continue
        if text.strip():
            GEMINI_MODELS.insert(0, model)  # remember the one that works
            return text
    raise last or RuntimeError("gemini: no usable model")


async def _groq_call(sess, model, prompt):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    if "gpt-oss" in model:  # reasoning model: keep thinking short or it eats all the tokens (empty answer)
        body["reasoning_effort"] = "low"
    async with sess.post(GROQ_URL, headers={"Authorization": f"Bearer {GROQ_KEY}"}, json=body) as r:
        if r.status != 200:
            raise await _err(r, f"groq[{model}]")
        j = await r.json(content_type=None)
    return (j["choices"][0]["message"].get("content") or "").strip()


async def _groq_discover(sess):
    async with sess.get(GROQ_LIST_URL, headers={"Authorization": f"Bearer {GROQ_KEY}"}) as r:
        if r.status != 200:
            raise await _err(r, "groq-list")
        j = await r.json(content_type=None)
    ids = [m.get("id", "") for m in j.get("data", []) if m.get("active", True)]
    ids = [i for i in ids if i and not _NOT_CHAT.search(i)]
    ids.sort(key=lambda i: (0 if "llama" in i and ("8b" in i or "instant" in i) else 1 if "llama" in i else 2, i))
    return ids[:3]


async def _groq(sess, prompt):
    last = None
    for model in GROQ_MODELS:
        if not _alive(model):
            continue
        try:
            text = await _groq_call(sess, model, prompt)
        except RuntimeError as ex:
            last = ex
            if any(c in str(ex) for c in (" HTTP 404", " HTTP 400")):  # decommissioned model
                _dead_models[model] = time.time() + DEAD_SECONDS
                continue
            raise  # 401/403/429/5xx: key or rate limit
        if text:
            return text
        last = RuntimeError(f"groq[{model}] empty answer")  # try the next model
    for model in await _groq_discover(sess):
        if not _alive(model):
            continue
        try:
            text = await _groq_call(sess, model, prompt)
        except RuntimeError as ex:
            last = ex
            _dead_models[model] = time.time() + DEAD_SECONDS
            continue
        if text:
            GROQ_MODELS.insert(0, model)
            return text
    raise last or RuntimeError("groq: no usable model")


async def _pollinations(sess, prompt):
    params = {"key": POLL_KEY} if POLL_KEY else None
    # the prompt travels inside the URL path: no newlines / slashes (they break path routing)
    flat = re.sub(r"\s+", " ", prompt).replace("/", "-")
    async with sess.get(POLL_URL + quote(flat, safe=""), params=params) as r:
        if r.status != 200:
            raise await _err(r, "pollinations")
        return await r.text()


def _providers():
    p = []
    if GEMINI_KEY:
        p.append(("gemini", _gemini))
    if GROQ_KEY:
        p.append(("groq", _groq))
    if POLL_KEY:  # without a key it answers HTTP 401 now
        p.append(("pollinations", _pollinations))
    if not p:
        LAST.update(ok=False, provider="", why="no AI key set")
    return p


async def ai_related(title: str, avoid=None):
    """Up to 8 'Song - Artist' names related to `title`, never the ones in `avoid`.
    [] if AI is off or everything failed (see LAST for the reason)."""
    if not ENABLED or not title:
        LAST.update(ok=None, provider="", why="AI_AUTOPLAY is off")
        return []
    norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
    # v4: the avoid-list is part of the cache key, so after new songs were played the AI is asked
    # again (before: the same answer came back for a whole hour -> the same songs again)
    key = norm(title) + "|" + norm(",".join(str(a) for a in list(avoid or [])[-6:]))
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        LAST.update(ok=True, provider="cache", why="")
        return list(hit[1])

    prompt = _prompt(title, avoid)
    end = time.time() + DEADLINE
    fails = []
    async with _sem:
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            for name, fn in _providers():
                left = end - time.time()
                if left <= 0.5:
                    fails.append("deadline")
                    break  # deadline reached: related.py continues with the old method
                if _bench_until.get(name, 0) > time.time():
                    fails.append(f"{name}: resting after an error")
                    continue
                try:
                    names = parse_names(await asyncio.wait_for(fn(sess, prompt), min(TIMEOUT, left)))
                except asyncio.CancelledError:
                    raise
                except Exception as ex:
                    _bench_until[name] = time.time() + BENCH_SECONDS
                    fails.append(f"{name}: {type(ex).__name__} {str(ex)[:60]}")
                    continue
                if names:
                    if len(_cache) > 300:
                        _cache.clear()
                    _cache[key] = (time.time(), names)
                    LAST.update(ok=True, provider=name, why="")
                    return names
                fails.append(f"{name}: empty answer")
    LAST.update(ok=False, provider="", why=" | ".join(fails) or "no AI key set (GEMINI_API_KEY / GROQ_API_KEY)")
    return []
