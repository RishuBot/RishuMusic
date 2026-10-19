import asyncio
import base64
import os
import time
from io import BytesIO
from urllib.parse import quote

import aiohttp
from gtts import gTTS
from pyrogram import filters
from pyrogram.enums import ChatAction

from RishuMusic import app  # v2: VIPMUSIC -> RishuMusic (agar ye VIPMUSIC bot me daal rahe ho to wapas badal do)
# v2: autoplay/ai.py se keys, model lists aur dead-model state reuse
from RishuMusic.utils.autoplay.ai import (
    DEAD_SECONDS, GEMINI_KEY, GEMINI_MODELS, GEMINI_URL,
    GROQ_KEY, GROQ_MODELS, GROQ_URL, POLL_KEY,
    _alive, _cfg, _dead_models, _err,
)

# v2: image settings (config.py / env me override ho sakte hain)
GEMINI_IMAGE_MODEL = _cfg("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
POLL_IMAGE_URL = _cfg("POLLINATIONS_IMAGE_URL", "https://gen.pollinations.ai/image/")

COOLDOWN = 8
_last = {}
SYSTEM = "You are a helpful assistant inside a Telegram bot. Keep answers clear and reasonably short."


def _on_cooldown(cmd, uid):
    left = COOLDOWN - (time.time() - _last.get((cmd, uid), 0))
    if left > 0:
        return int(left) + 1
    _last[(cmd, uid)] = time.time()
    return 0


def _get_prompt(message):
    if len(message.command) > 1:
        return message.text.split(None, 1)[1].strip()
    r = message.reply_to_message
    return ((r.text or r.caption or "").strip()) if r else ""


# ================= /ai =================
async def _gemini_chat(sess, prompt):  # v2: autoplay ke _gemini ka chat version (2048 tokens)
    last = None
    for model in GEMINI_MODELS:
        if not _alive(model):
            continue
        body = {
            "systemInstruction": {"parts": [{"text": SYSTEM}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048},
        }
        async with sess.post(GEMINI_URL.format(model=model),
                             headers={"x-goog-api-key": GEMINI_KEY}, json=body) as r:
            if r.status in (404, 400):  # retired/unknown model -> skip kuch ghante
                last = await _err(r, f"gemini[{model}]")
                _dead_models[model] = time.time() + DEAD_SECONDS
                continue
            if r.status != 200:
                raise await _err(r, f"gemini[{model}]")
            j = await r.json(content_type=None)
        try:
            text = "".join(p.get("text", "") for p in j["candidates"][0]["content"]["parts"]).strip()
        except Exception:
            text = ""
        if text:
            return text
        last = RuntimeError(f"gemini[{model}] empty answer")
    raise last or RuntimeError("gemini: no usable model")


async def _groq_chat(sess, prompt):  # v2
    last = None
    for model in GROQ_MODELS:
        if not _alive(model):
            continue
        body = {
            "model": model,
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        if "gpt-oss" in model:
            body["reasoning_effort"] = "low"
        async with sess.post(GROQ_URL, headers={"Authorization": f"Bearer {GROQ_KEY}"}, json=body) as r:
            if r.status in (404, 400):
                last = await _err(r, f"groq[{model}]")
                _dead_models[model] = time.time() + DEAD_SECONDS
                continue
            if r.status != 200:
                raise await _err(r, f"groq[{model}]")
            j = await r.json(content_type=None)
        text = (j["choices"][0]["message"].get("content") or "").strip()
        if text:
            return text
        last = RuntimeError(f"groq[{model}] empty answer")
    raise last or RuntimeError("groq: no usable model")


async def ask_ai(prompt):
    providers = []
    if GEMINI_KEY:
        providers.append(_gemini_chat)
    if GROQ_KEY:
        providers.append(_groq_chat)
    if not providers:
        raise RuntimeError("GEMINI_API_KEY / GROQ_API_KEY set nahi hai")
    fails = []
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=40)) as sess:
        for fn in providers:
            try:
                return await fn(sess, prompt)
            except Exception as e:
                fails.append(str(e)[:120])
    raise RuntimeError(" | ".join(fails))


@app.on_message(filters.command(["ai", "ask", "chatgpt"]) & ~filters.bot)
async def ai_cmd(client, message):
    uid = message.from_user.id if message.from_user else 0
    if left := _on_cooldown("ai", uid):
        return await message.reply_text(f"⏳ {left}s baad try karo.")
    prompt = _get_prompt(message)
    if not prompt:
        return await message.reply_text("**Usage:** `/ai your question` ya kisi message pe reply karke `/ai`")
    wait = await message.reply_text("🤖 Soch raha hu...")
    try:
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        answer = await ask_ai(prompt)
        chunks = [answer[i:i + 4000] for i in range(0, len(answer), 4000)]
        await wait.edit_text(chunks[0])
        for ch in chunks[1:]:
            await message.reply_text(ch)
    except Exception as e:
        await wait.edit_text(f"❌ AI error: `{e}`")


# ================= /tts (v1 jaisa, no change) =================
def _make_tts(text, lang, path):
    gTTS(text=text, lang=lang).save(path)


@app.on_message(filters.command(["tts"]) & ~filters.bot)
async def tts_cmd(client, message):
    uid = message.from_user.id if message.from_user else 0
    if left := _on_cooldown("tts", uid):
        return await message.reply_text(f"⏳ {left}s baad try karo.")
    lang, args = "en", message.command[1:]
    if args and len(args[0]) in (2, 5) and (len(args) > 1 or message.reply_to_message):
        lang, text = args[0].lower(), " ".join(args[1:]).strip()
    else:
        text = " ".join(args).strip()
    if not text and message.reply_to_message:
        text = (message.reply_to_message.text or message.reply_to_message.caption or "").strip()
    if not text:
        return await message.reply_text("**Usage:** `/tts hello` ya `/tts hi namaste` (hi = language code)")
    path = f"tts_{message.chat.id}_{message.id}.mp3"
    wait = await message.reply_text("🎙 Voice bana raha hu...")
    try:
        await client.send_chat_action(message.chat.id, ChatAction.RECORD_AUDIO)
        await asyncio.to_thread(_make_tts, text[:1000], lang, path)
        await client.send_audio(message.chat.id, path, title="TTS", performer="AI Voice",
                                reply_to_message_id=message.id)
        await wait.delete()
    except ValueError:
        await wait.edit_text("❌ Language code galat hai (en, hi, ur, es...).")
    except Exception as e:
        await wait.edit_text(f"❌ TTS error: `{e}`")
    finally:
        if os.path.exists(path):
            os.remove(path)


# ================= /image =================
async def _gemini_image(sess, prompt):  # v2: Gemini image model (same key)
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    async with sess.post(GEMINI_URL.format(model=GEMINI_IMAGE_MODEL),
                         headers={"x-goog-api-key": GEMINI_KEY}, json=body) as r:
        if r.status != 200:
            raise await _err(r, f"gemini-image[{GEMINI_IMAGE_MODEL}]")
        j = await r.json(content_type=None)
    for p in j["candidates"][0]["content"]["parts"]:
        d = p.get("inlineData") or p.get("inline_data")
        if d and d.get("data"):
            return base64.b64decode(d["data"])
    raise RuntimeError("gemini-image: image nahi mili")


async def _poll_image(sess, prompt):  # v2: key ke saath (bina key 401 aata hai)
    url = POLL_IMAGE_URL + quote(prompt, safe="")
    async with sess.get(url, params={"key": POLL_KEY, "width": 1024, "height": 1024, "nologo": "true"}) as r:
        if r.status != 200:
            raise await _err(r, "pollinations-image")
        if "image" not in r.headers.get("content-type", ""):
            raise RuntimeError("pollinations-image: image nahi mili")
        return await r.read()


async def gen_image(prompt):
    providers = []
    if GEMINI_KEY:
        providers.append(_gemini_image)
    if POLL_KEY:
        providers.append(_poll_image)
    if not providers:
        raise RuntimeError("GEMINI_API_KEY ya POLLINATIONS_KEY set nahi hai")
    fails = []
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=90)) as sess:
        for fn in providers:
            try:
                return await fn(sess, prompt)
            except Exception as e:
                fails.append(str(e)[:120])
    raise RuntimeError(" | ".join(fails))


@app.on_message(filters.command(["image", "imagine", "img"]) & ~filters.bot)
async def image_cmd(client, message):
    uid = message.from_user.id if message.from_user else 0
    if left := _on_cooldown("image", uid):
        return await message.reply_text(f"⏳ {left}s baad try karo.")
    prompt = _get_prompt(message)
    if not prompt:
        return await message.reply_text("**Usage:** `/image a cat riding a bike`")
    wait = await message.reply_text("🎨 Image bana raha hu...")
    try:
        await client.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)
        data = await gen_image(prompt)
        bio = BytesIO(data)
        bio.name = "ai_image.png"
        await client.send_photo(message.chat.id, bio, caption=f"🖼 **Prompt:** `{prompt[:900]}`",
                                reply_to_message_id=message.id)
        await wait.delete()
    except Exception as e:
        await wait.edit_text(f"❌ Image error: `{e}`")