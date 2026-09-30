# thumbnails.py v8 (CHANGED): naya frosted-panel design (gen_thumb) + purana get_thumb(videoid, user_id) wrapper
import os
import re
import traceback

import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

try:
    from py_yt import VideosSearch  # v8: Youtube.py wali library (youtubesearchpython tootti hai)
except ImportError:
    from youtubesearchpython.__future__ import VideosSearch

from config import YOUTUBE_IMG_URL

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

ASSETS = "RishuMusic/assets" 

PANEL_W, PANEL_H = 763, 545
PANEL_X = (1280 - PANEL_W) // 2
PANEL_Y = 88
TRANSPARENCY = 170
INNER_OFFSET = 36

THUMB_W, THUMB_H = 542, 273
THUMB_X = PANEL_X + (PANEL_W - THUMB_W) // 2
THUMB_Y = PANEL_Y + INNER_OFFSET

TITLE_X = 377
META_X = 377
TITLE_Y = THUMB_Y + THUMB_H + 10
META_Y = TITLE_Y + 45

BAR_X, BAR_Y = 388, META_Y + 45
BAR_RED_LEN = 280
BAR_TOTAL_LEN = 480

ICONS_W, ICONS_H = 415, 45
ICONS_X = PANEL_X + (PANEL_W - ICONS_W) // 2
ICONS_Y = BAR_Y + 48

MAX_TITLE_WIDTH = 580


def trim_to_width(text, font, max_width):
    ellipsis = "…"
    if (font.getbbox(text)[2] - font.getbbox(text)[0]) <= max_width:
        return text
    for i in range(len(text) - 1, 0, -1):
        cropped = text[:i] + ellipsis
        if (font.getbbox(cropped)[2] - font.getbbox(cropped)[0]) <= max_width:
            return cropped
    return ellipsis


async def gen_thumb(videoid: str) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_v4.png")

    # v8: cache use hota hai (autoplay pehle se thumbnail bana leta hai)
    if os.path.exists(cache_path):
        return cache_path

    try:
        results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
        try:
            results_data = await results.next()
            result_items = results_data.get("result", [])
            if not result_items:
                raise ValueError("No results found.")
            data = result_items[0]
            title = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
            thumbnail = data.get("thumbnails", [{}])[0].get("url", YOUTUBE_IMG_URL)
            duration = data.get("duration")
            views = data.get("viewCount", {}).get("short", "Unknown Views")
        except Exception:
            traceback.print_exc()
            title, duration, views = "Unsupported Title", None, "Unknown Views"
            thumbnail = f"https://i.ytimg.com/vi/{videoid}/hqdefault.jpg"  # v8: fallback real thumbnail

        is_live = not duration or str(duration).strip().lower() in {"", "live", "live now"}
        duration_text = "Live" if is_live else duration or "Unknown Mins"

        thumb_path = os.path.join(CACHE_DIR, f"thumb{videoid}.png")
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status != 200:  # v8: bad status par ytimg fallback
                    async with session.get(f"https://i.ytimg.com/vi/{videoid}/hqdefault.jpg") as r2:
                        content = await r2.read()
                else:
                    content = await resp.read()
        async with aiofiles.open(thumb_path, "wb") as f:
            await f.write(content)

        base = Image.open(thumb_path).resize((1280, 720)).convert("RGBA")
        bg = ImageEnhance.Brightness(base.filter(ImageFilter.BoxBlur(10))).enhance(0.6)

        panel_area = bg.crop((PANEL_X, PANEL_Y, PANEL_X + PANEL_W, PANEL_Y + PANEL_H))
        overlay = Image.new("RGBA", (PANEL_W, PANEL_H), (255, 255, 255, TRANSPARENCY))
        frosted = Image.alpha_composite(panel_area, overlay)
        mask = Image.new("L", (PANEL_W, PANEL_H), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, PANEL_W, PANEL_H), 50, fill=255)
        bg.paste(frosted, (PANEL_X, PANEL_Y), mask)

        draw = ImageDraw.Draw(bg)
        try:
            title_font = ImageFont.truetype(f"{ASSETS}/font2.ttf", 32)
            regular_font = ImageFont.truetype(f"{ASSETS}/font.ttf", 18)
        except OSError:
            title_font = regular_font = ImageFont.load_default()

        thumb = base.resize((THUMB_W, THUMB_H))
        tmask = Image.new("L", thumb.size, 0)
        ImageDraw.Draw(tmask).rounded_rectangle((0, 0, THUMB_W, THUMB_H), 20, fill=255)
        bg.paste(thumb, (THUMB_X, THUMB_Y), tmask)

        draw.text((TITLE_X, TITLE_Y), trim_to_width(title, title_font, MAX_TITLE_WIDTH), fill="black", font=title_font)
        draw.text((META_X, META_Y), f"YouTube | {views}", fill="black", font=regular_font)

        draw.line([(BAR_X, BAR_Y), (BAR_X + BAR_RED_LEN, BAR_Y)], fill="red", width=6)
        draw.line([(BAR_X + BAR_RED_LEN, BAR_Y), (BAR_X + BAR_TOTAL_LEN, BAR_Y)], fill="gray", width=5)
        draw.ellipse([(BAR_X + BAR_RED_LEN - 7, BAR_Y - 7), (BAR_X + BAR_RED_LEN + 7, BAR_Y + 7)], fill="red")

        draw.text((BAR_X, BAR_Y + 15), "00:00", fill="black", font=regular_font)
        end_text = "Live" if is_live else duration_text
        draw.text((BAR_X + BAR_TOTAL_LEN - (90 if is_live else 60), BAR_Y + 15), end_text, fill="red" if is_live else "black", font=regular_font)

        icons_path = f"{ASSETS}/play_icons.png"
        if os.path.isfile(icons_path):
            ic = Image.open(icons_path).resize((ICONS_W, ICONS_H)).convert("RGBA")
            r, g, b, a = ic.split()
            black_ic = Image.merge("RGBA", (r.point(lambda *_: 0), g.point(lambda *_: 0), b.point(lambda *_: 0), a))
            bg.paste(black_ic, (ICONS_X, ICONS_Y), black_ic)

        try:
            os.remove(thumb_path)
        except OSError:
            pass

        bg.save(cache_path)
        return cache_path
    except Exception:
        traceback.print_exc()  # v8: asli error console me
        return YOUTUBE_IMG_URL


async def get_thumb(videoid, user_id=None):
    """v8: purane saare call sites (call.py, stream.py, skip.py, callback.py) ke liye wrapper. user_id ab use nahi hota."""
    return await gen_thumb(videoid)
