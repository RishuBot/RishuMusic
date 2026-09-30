# autoplay v4 (CHANGED) - public API (hooks sirf yahi functions call karte hain)
import asyncio
from .state import ENABLED, READY, TASKS, AUTO, mark_seen, reset
from .prefetch import start_prefetch

__all__ = ["is_on", "set_on", "note_queued", "enqueue_next", "clear"]


def is_on(chat_id):
    return ENABLED.get(chat_id, False)


def set_on(chat_id, value, ref=None):
    ENABLED[chat_id] = value
    if value and ref:
        mark_seen(chat_id, ref[0], ref[1])  # v4
        start_prefetch(chat_id, ref[0], ref[1])
    if not value:
        reset(chat_id)


def note_queued(chat_id, vidid, title):
    """put_queue se call hota hai: song history me + prefetch trigger."""
    if not vidid:
        return
    mark_seen(chat_id, vidid, title)
    if is_on(chat_id):
        start_prefetch(chat_id, vidid, title)


def clear(chat_id):
    """stop/end par call karo."""
    reset(chat_id)


def _fmt(sec):
    m, s = divmod(int(sec or 0), 60)
    return f"{m}:{s:02d}"


async def _wait_first(chat_id, timeout=20):
    for _ in range(int(timeout / 0.5)):
        if READY[chat_id]:
            return
        t = TASKS.get(chat_id)
        if not t or t.done():
            return
        await asyncio.sleep(0.5)


async def enqueue_next(chat_id, original_chat_id=None):
    """Queue khali hone par call karo. True = normal queue me next song aa gaya."""
    if not is_on(chat_id):
        return False
    if not READY[chat_id]:
        await _wait_first(chat_id)
    if not READY[chat_id]:
        return False
    t = READY[chat_id].pop(0)
    mark_seen(chat_id, t["vidid"], t["title"])
    AUTO[chat_id] = t["vidid"]
    from RishuMusic.utils.stream.queue import put_queue   # path adjust karo agar alag ho

    await put_queue(
        chat_id, original_chat_id or chat_id, t["file"], t["title"],
        _fmt(t["duration"]), "Autoplay", t["vidid"], 0, "audio",
    )
    return True
