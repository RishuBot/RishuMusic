# autoplay v4 (CHANGED) - related songs ab song ke NAAM se check hote hain
import asyncio
import re
import yt_dlp

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


async def fetch_related(vidid, title):
    loop = asyncio.get_running_loop()
    name = clean_name(title)
    sources = (
        f"ytsearch25:{name} songs",                                   # naam se
        f"https://www.youtube.com/watch?v={vidid}&list=RD{vidid}",    # YouTube Mix (v4: dono use)
    )
    me = tokens(title)
    out, picked = [], [me]
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
