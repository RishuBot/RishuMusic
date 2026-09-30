# autoplay v4 (CHANGED) - per-chat state
import os
from .related import tokens, similar
from collections import defaultdict, deque

TARGET = 5                                    # kitne related songs ready rakhne hain
ENABLED = {}                                  # chat_id -> bool
HISTORY = defaultdict(lambda: deque(maxlen=300))  # chat_id -> played/queued vidids
TITLES = defaultdict(lambda: deque(maxlen=300))  # v4: title token-sets
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
