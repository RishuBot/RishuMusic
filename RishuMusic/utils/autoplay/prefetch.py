# autoplay v5 (CHANGED) - history loaded from MongoDB, AI gets the recent-songs avoid-list, Owner DM when AI is silent
# autoplay v4 (CHANGED) - background me 5 related songs pre-download
import asyncio
from .state import (READY, TASKS, REF, AUTO, TARGET, RECENT, seen, reset, cancel_task, load_history)
from .related import fetch_related, tokens, similar
from . import ai as _ai


_told = {"ok": False, "fail": 0.0}


async def _tell_owner():
    """v5: no logs? The Owner gets ONE DM when AI works for the first time, and one (max every 30 min)
    when it did not give anything - so you can see whether 'same songs' means the AI is silent."""
    import time

    try:
        import config
        from RishuMusic import app

        st = _ai.LAST
        if st.get("ok") and st.get("provider") != "cache" and not _told["ok"]:
            _told["ok"] = True
            await app.send_message(config.OWNER_ID, f"🤖 <b>AI autoplay works</b> (provider: <code>{st['provider']}</code>)")
        elif st.get("ok") is False and time.time() - _told["fail"] > 1800:
            _told["fail"] = time.time()
            await app.send_message(
                config.OWNER_ID,
                "⚠️ <b>AI autoplay gave no songs</b>, the old method was used.\n"
                f"<code>{(st.get('why') or '')[:300]}</code>\n"
                "Add GEMINI_API_KEY or GROQ_API_KEY (free) in your variables.",
            )
    except Exception:
        pass


async def _worker(chat_id, vidid, title):
    # YouTube class tumhare repo ka (path apne hisaab se adjust karo)
    from RishuMusic import YouTube

    await load_history(chat_id)  # v5: songs played before the last restart count as seen
    cands = await fetch_related(vidid, title, avoid=list(RECENT[chat_id]))
    await _tell_owner()
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
