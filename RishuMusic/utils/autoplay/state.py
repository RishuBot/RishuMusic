# autoplay v1 (NEW) - per-chat state
import os
from .related import norm
from collections import defaultdict, deque

TARGET = 5                                    # kitne related songs ready rakhne hain
ENABLED = {}                                  # chat_id -> bool
HISTORY = defaultdict(lambda: deque(maxlen=300))  # chat_id -> played/queued vidids
TITLES = defaultdict(lambda: deque(maxlen=300))  # v2: normalized titles
READY = defaultdict(list)                     # chat_id -> [{vidid,title,duration,file}]
TASKS = {}                                    # chat_id -> asyncio.Task
REF = {}                                      # chat_id -> vidid jiske related fetch hue
AUTO = {}                                     # chat_id -> vidid jo autoplay ne queue kiya


def seen(chat_id, vidid, title=None):
    if vidid in HISTORY[chat_id]:
        return True
    return title is not None and norm(title) in TITLES[chat_id]   # v2


def mark_seen(chat_id, vidid, title=None):
    if vidid and vidid not in HISTORY[chat_id]:
        HISTORY[chat_id].append(vidid)
    if title and norm(title) not in TITLES[chat_id]:
        TITLES[chat_id].append(norm(title))                        # v2


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
