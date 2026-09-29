# autoplay v2 (CHANGED) - related songs ab song ke NAAM se check hote hain
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


def norm(title):
    """Same song alag upload/naam se bhi repeat na ho."""
    return re.sub(r"[^a-z0-9]", "", clean_name(title).lower())


def _extract(url):
    with yt_dlp.YoutubeDL(_OPTS) as y:
        return y.extract_info(url, download=False)


async def fetch_related(vidid, title):
    loop = asyncio.get_running_loop()
    name = clean_name(title)
    sources = (
        f"ytsearch25:{name} songs",                                   # v2: naam se
        f"https://www.youtube.com/watch?v={vidid}&list=RD{vidid}",    # fallback: mix
    )
    me = norm(title)
    for url in sources:
        try:
            info = await loop.run_in_executor(None, _extract, url)
        except Exception:
            continue
        out = []
        for e in (info or {}).get("entries") or []:
            if not e or not e.get("id") or e["id"] == vidid:
                continue
            t = e.get("title") or "Unknown"
            if norm(t) == me:                 # wahi song dobara nahi
                continue
            d = e.get("duration") or 0
            if d and (d < 60 or d > 720):
                continue
            out.append({"vidid": e["id"], "title": t, "duration": d})
        if out:
            return out
    return []
