# autoplay v4 (CHANGED) - background me 5 related songs pre-download
import asyncio
from .state import (READY, TASKS, REF, AUTO, TARGET, seen, reset, cancel_task)
from .related import fetch_related, tokens, similar


async def _worker(chat_id, vidid, title):
    # YouTube class tumhare repo ka (path apne hisaab se adjust karo)
    from RishuMusic import YouTube

    cands = await fetch_related(vidid, title)
    for c in cands:
        if len(READY[chat_id]) >= TARGET:
            break
        ctk = tokens(c["title"])
        if seen(chat_id, c["vidid"], c["title"]) or any(
            r["vidid"] == c["vidid"] or similar(ctk, tokens(r["title"])) for r in READY[chat_id]
        ):  # v4
            continue
        try:
            file, _ = await YouTube.download(c["vidid"], None, videoid=True, video=False)  # v3: fixed
        except asyncio.CancelledError:
            raise
        except Exception:
            continue
        if file:
            READY[chat_id].append({**c, "file": file})


def start_prefetch(chat_id, vidid, title):
    if REF.get(chat_id) == vidid and chat_id in TASKS:
        return                                   # same song, already chal raha
    if AUTO.get(chat_id) == vidid:
        cancel_task(chat_id)                     # autoplay wala song: purane ready rakho, top-up karo
    else:
        reset(chat_id)                           # manual song: purane related stale, naye banao
    REF[chat_id] = vidid
    TASKS[chat_id] = asyncio.create_task(_worker(chat_id, vidid, title))
