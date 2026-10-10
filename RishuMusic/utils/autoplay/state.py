# autoplay v4 (CHANGED) - per-chat state
# v5: RECENT (raw titles for the AI avoid-list) + history saved in MongoDB, so a restart no longer
#     makes the same songs come back
import asyncio
import os
from .related import tokens, similar
from collections import defaultdict, deque

TARGET = 5                                    # kitne related songs ready rakhne hain
ENABLED = {}                                  # chat_id -> bool
HISTORY = defaultdict(lambda: deque(maxlen=300))  # chat_id -> played/queued vidids
TITLES = defaultdict(lambda: deque(maxlen=300))  # v4: title token-sets
RECENT = defaultdict(lambda: deque(maxlen=12))   # v5: last raw titles (given to the AI as 'do not repeat')
_LOADED = set()                                 # v5: chats whose saved history was already loaded
READY = defaultdict(list)                     # chat_id -> [{vidid,title,duration,file}]
TASKS = {}                                    # chat_id -> asyncio.Task
REF = {}                                      # chat_id -> vidid jiske related fetch hue
AUTO = {}                                     # chat_id -> vidid jo autoplay ne queue kiya


def seen(chat_id, vidid, title=None):
    if vidid in HISTORY[chat_id]:
        return True
    if title:                                                       # v4: fuzzy title match
        tk = tokens(title)
        return any(similar(tk, x) for x in TITLES[chat_id])
    return False


def mark_seen(chat_id, vidid, title=None):
    if vidid and vidid not in HISTORY[chat_id]:
        HISTORY[chat_id].append(vidid)
    if title:
        TITLES[chat_id].append(tokens(title))                       # v4
        RECENT[chat_id].append(title)                               # v5
    _persist(chat_id, vidid, title)                                 # v5


def _col():
    try:
        from RishuMusic.core.mongo import mongodb

        return mongodb.autoplay_history
    except Exception:
        return None


def _persist(chat_id, vidid, title):
    """Fire-and-forget: keep the last 300 songs of each chat in MongoDB."""
    col = _col()
    if col is None or not vidid:
        return
    try:
        asyncio.get_running_loop().create_task(
            col.update_one(
                {"_id": chat_id},
                {"$push": {"v": {"$each": [vidid], "$slice": -300}, "t": {"$each": [title or ""], "$slice": -300}}},
                upsert=True,
            )
        )
    except Exception:
        pass


async def load_history(chat_id):
    """Once per chat after a restart: read the saved history back (so old songs are not repeated)."""
    if chat_id in _LOADED:
        return
    _LOADED.add(chat_id)
    col = _col()
    if col is None:
        return
    try:
        doc = await col.find_one({"_id": chat_id})
    except Exception:
        return
    if not doc:
        return
    for v in doc.get("v", []):
        if v and v not in HISTORY[chat_id]:
            HISTORY[chat_id].append(v)
    for t in doc.get("t", []):
        if t:
            TITLES[chat_id].append(tokens(t))
    for t in [x for x in doc.get("t", []) if x][-12:]:
        RECENT[chat_id].append(t)


def cancel_task(chat_id):
    t = TASKS.pop(chat_id, None)
    if t and not t.done():
        t.cancel()


def _rm(path):
    try:
        os.remove(path)
    except Exception:
        pass


def reset(chat_id):
    """Task cancel + prefetched files delete (history rehne dete hain)."""
    cancel_task(chat_id)
    for item in READY.pop(chat_id, []):
        _rm(item["file"])
    REF.pop(chat_id, None)
    AUTO.pop(chat_id, None)
