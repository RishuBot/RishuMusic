# autoplay v5 (CHANGED) - AI suggests the first 5 related songs (utils/autoplay/ai.py); old search + YouTube Mix fill the rest / act as fallback
# autoplay v4 (CHANGED) - related songs ab song ke NAAM se check hote hain
import asyncio
import re
import yt_dlp

from .ai import ai_related  # v5

_JUNK = re.compile(
    r"\(.*?\)|\[.*?\]|\|.*|\b(official|video|audio|lyrics?|lyrical|full song|hd|4k|"
    r"remix|slowed|reverb)\b|\b(ft|feat)\b\.?.*",
    re.I,
)
_OPTS = {"quiet": True, "no_warnings": True, "extract_flat": True,
         "skip_download": True, "playlistend": 30}


def clean_name(title):
    t = _JUNK.sub(" ", title or "")
    return re.sub(r"\s+", " ", t).strip(" -_")


def tokens(title):
    """v4: title ke important words, order ke saath (fuzzy match ke liye)."""
    t = re.sub(r"[^a-z0-9 ]", " ", clean_name(title).lower())
    return tuple(w for w in t.split() if len(w) > 1)


def similar(a, b):
    """v4: True agar dono title lagbhag same song ke hain (alag upload/naam bhi)."""
    if not a or not b:
        return False
    if a[:2] == b[:2] and len(a) >= 2 and len(b) >= 2:      # shuruaat ke 2 words same
        return True
    if a[0] == b[0] and len(a[0]) >= 5:                     # pehla lamba word same (jaise "kesariya")
        return True
    sa, sb = set(a), set(b)
    return len(sa & sb) / min(len(sa), len(sb)) >= 0.75


def norm(title):
    return re.sub(r"[^a-z0-9]", "", clean_name(title).lower())


def _extract(url):
    with yt_dlp.YoutubeDL(_OPTS) as y:
        return y.extract_info(url, download=False)


_SEARCH_SEM = asyncio.Semaphore(2)  # v5: never run 5 yt-dlp searches at once (CPU burst slows the voice stream)


def _search_one(name):
    """v5: top YouTube results for one AI-suggested song name."""
    return _extract(f"ytsearch3:{name}")


async def _search_limited(loop, name):
    async with _SEARCH_SEM:
        return await loop.run_in_executor(None, _search_one, name)


def _usable(e, vidid, picked):
    """Entry passes the same filters the old code used (not current song, not a duplicate, sane length)."""
    if not e or not e.get("id") or e["id"] == vidid:
        return False
    if any(similar(tokens(e.get("title") or ""), p) for p in picked):
        return False
    d = e.get("duration") or 0
    return not (d and (d < 60 or d > 720))


async def fetch_related(vidid, title, avoid=None):
    loop = asyncio.get_running_loop()
    name = clean_name(title)
    sources = (
        f"ytsearch25:{name} songs",                                   # naam se
        f"https://www.youtube.com/watch?v={vidid}&list=RD{vidid}",    # YouTube Mix (v4: dono use)
    )
    me = tokens(title)
    out, picked = [], [me]

    # v5: AI suggests 5 related song NAMES -> each is searched on YouTube and goes to the FRONT
    # of the list (prefetch downloads in this order). If AI or the search fails, nothing is lost:
    # the old sources below still fill the list exactly like before.
    try:
        names = await ai_related(title, avoid)  # v6: AI is told what was already played
        found = await asyncio.gather(
            *[_search_limited(loop, n) for n in names],
            return_exceptions=True,
        )
        for info in found:
            if isinstance(info, Exception):
                continue
            for e in (info or {}).get("entries") or []:
                if _usable(e, vidid, picked):
                    picked.append(tokens(e.get("title") or ""))
                    out.append({"vidid": e["id"], "title": e.get("title") or "Unknown",
                                "duration": e.get("duration") or 0})
                    break  # one result per suggested name
    except asyncio.CancelledError:
        raise
    except Exception:
        pass
    for url in sources:
        try:
            info = await loop.run_in_executor(None, _extract, url)
        except Exception:
            continue
        for e in (info or {}).get("entries") or []:
            if not e or not e.get("id") or e["id"] == vidid:
                continue
            t = e.get("title") or "Unknown"
            tk = tokens(t)
            if any(similar(tk, p) for p in picked):   # v4: same song ka koi bhi version skip
                continue
            d = e.get("duration") or 0
            if d and (d < 60 or d > 720):
                continue
            picked.append(tk)
            out.append({"vidid": e["id"], "title": t, "duration": d})
    return out
