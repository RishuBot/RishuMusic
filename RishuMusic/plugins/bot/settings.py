from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.errors import MessageNotModified
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from RishuMusic import app
from RishuMusic.utils.database import (
    add_nonadmin_chat,
    get_authuser,
    get_authuser_names,
    get_playmode,
    get_playtype,
    get_upvote_count,
    is_nonadmin_chat,
    is_skipmode,
    remove_nonadmin_chat,
    set_playmode,
    set_playtype,
    set_upvotes,
    skip_off,
    skip_on,
)
from RishuMusic.utils.decorators.admins import ActualAdminCB
from RishuMusic.utils.decorators.language import language, languageCB
from RishuMusic.utils.inline.settings import (
    auth_users_markup,
    playmode_users_markup,
    setting_markup,
    vote_mode_markup,
)
from RishuMusic.utils.inline.start import private_panel
from config import BANNED_USERS, OWNER_ID


@app.on_message(
    filters.command(["settings", "setting"]) & filters.group & ~BANNED_USERS
)
@language
async def settings_mar(client, message: Message, _):
    buttons = setting_markup(_)
    await message.reply_text(
        _["setting_1"].format(app.mention, message.chat.id, message.chat.title),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


@app.on_callback_query(filters.regex("settings_helper") & ~BANNED_USERS)
@languageCB
async def settings_cb(client, CallbackQuery, _):
    try:
        await CallbackQuery.answer(_["set_cb_5"])
    except:
        pass
    buttons = setting_markup(_)
    return await CallbackQuery.edit_message_text(
        _["setting_1"].format(
            app.mention,
            CallbackQuery.message.chat.id,
            CallbackQuery.message.chat.title,
        ),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


@app.on_callback_query(filters.regex("settingsback_helper") & ~BANNED_USERS)
@languageCB
async def settings_back_markup(client, CallbackQuery: CallbackQuery, _):
    try:
        await CallbackQuery.answer()
    except:
        pass
    if CallbackQuery.message.chat.type == ChatType.PRIVATE:
        await app.resolve_peer(OWNER_ID)
        OWNER = OWNER_ID
        buttons = private_panel(_)
        return await CallbackQuery.edit_message_text(
            _["start_2"].format(CallbackQuery.from_user.mention, app.mention),
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    else:
        buttons = setting_markup(_)
        return await CallbackQuery.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(buttons)
        )


@app.on_callback_query(
    filters.regex(
        pattern=r"^(SEARCHANSWER|PLAYMODEANSWER|PLAYTYPEANSWER|AUTHANSWER|ANSWERVOMODE|VOTEANSWER|PM|AU|VM)$"
    )
    & ~BANNED_USERS
)
@languageCB
async def without_Admin_rights(client, CallbackQuery, _):
    command = CallbackQuery.matches[0].group(1)
    if command == "SEARCHANSWER":
        try:
            return await CallbackQuery.answer(_["setting_2"], show_alert=True)
        except:
            return
    if command == "PLAYMODEANSWER":
        try:
            return await CallbackQuery.answer(_["setting_5"], show_alert=True)
        except:
            return
    if command == "PLAYTYPEANSWER":
        try:
            return await CallbackQuery.answer(_["setting_6"], show_alert=True)
        except:
            return
    if command == "AUTHANSWER":
        try:
            return await CallbackQuery.answer(_["setting_3"], show_alert=True)
        except:
            return
    if command == "VOTEANSWER":
        try:
            return await CallbackQuery.answer(
                _["setting_8"],
                show_alert=True,
            )
        except:
            return
    if command == "ANSWERVOMODE":
        current = await get_upvote_count(CallbackQuery.message.chat.id)
        try:
            return await CallbackQuery.answer(
                _["setting_9"].format(current),
                show_alert=True,
            )
        except:
            return
    if command == "PM":
        try:
            await CallbackQuery.answer(_["set_cb_2"], show_alert=True)
        except:
            pass
        playmode = await get_playmode(CallbackQuery.message.chat.id)
        if playmode == "Direct":
            Direct = True
        else:
            Direct = None
        is_non_admin = await is_nonadmin_chat(CallbackQuery.message.chat.id)
        if not is_non_admin:
            Group = True
        else:
            Group = None
        playty = await get_playtype(CallbackQuery.message.chat.id)
        if playty == "Everyone":
            Playtype = None
        else:
            Playtype = True
        buttons = playmode_users_markup(_, Direct, Group, Playtype)
    if command == "AU":
        try:
            await CallbackQuery.answer(_["set_cb_1"], show_alert=True)
        except:
            pass
        is_non_admin = await is_nonadmin_chat(CallbackQuery.message.chat.id)
        if not is_non_admin:
            buttons = auth_users_markup(_, True)
        else:
            buttons = auth_users_markup(_)
    if command == "VM":
        mode = await is_skipmode(CallbackQuery.message.chat.id)
        current = await get_upvote_count(CallbackQuery.message.chat.id)
        buttons = vote_mode_markup(_, current, mode)
    try:
        return await CallbackQuery.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except MessageNotModified:
        return


@app.on_callback_query(filters.regex("FERRARIUDTI") & ~BANNED_USERS)
@ActualAdminCB
async def addition(client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    mode = callback_data.split(None, 1)[1]
    if not await is_skipmode(CallbackQuery.message.chat.id):
        return await CallbackQuery.answer(_["setting_10"], show_alert=True)
    current = await get_upvote_count(CallbackQuery.message.chat.id)
    if mode == "M":
        final = current - 2
        print(final)
        if final == 0:
            return await CallbackQuery.answer(
                _["setting_11"],
                show_alert=True,
            )
        if final <= 2:
            final = 2
        await set_upvotes(CallbackQuery.message.chat.id, final)
    else:
        final = current + 2
        print(final)
        if final == 17:
            return await CallbackQuery.answer(
                _["setting_12"],
                show_alert=True,
            )
        if final >= 15:
            final = 15
        await set_upvotes(CallbackQuery.message.chat.id, final)
    buttons = vote_mode_markup(_, final, True)
    try:
        return await CallbackQuery.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except MessageNotModified:
        return


@app.on_callback_query(
    filters.regex(pattern=r"^(MODECHANGE|CHANNELMODECHANGE|PLAYTYPECHANGE)$")
    & ~BANNED_USERS
)
@ActualAdminCB
async def playmode_ans(client, CallbackQuery, _):
    command = CallbackQuery.matches[0].group(1)
    if command == "CHANNELMODECHANGE":
        is_non_admin = await is_nonadmin_chat(CallbackQuery.message.chat.id)
        if not is_non_admin:
            await add_nonadmin_chat(CallbackQuery.message.chat.id)
            Group = None
        else:
            await remove_nonadmin_chat(CallbackQuery.message.chat.id)
            Group = True
        playmode = await get_playmode(CallbackQuery.message.chat.id)
        if playmode == "Direct":
            Direct = True
        else:
            Direct = None
        playty = await get_playtype(CallbackQuery.message.chat.id)
        if playty == "Everyone":
            Playtype = None
        else:
            Playtype = True
        buttons = playmode_users_markup(_, Direct, Group, Playtype)
    if command == "MODECHANGE":
        try:
            await CallbackQuery.answer(_["set_cb_3"], show_alert=True)
        except:
            pass
        playmode = await get_playmode(CallbackQuery.message.chat.id)
        if playmode == "Direct":
            await set_playmode(CallbackQuery.message.chat.id, "Inline")
            Direct = None
        else:
            await set_playmode(CallbackQuery.message.chat.id, "Direct")
            Direct = True
        is_non_admin = await is_nonadmin_chat(CallbackQuery.message.chat.id)
        if not is_non_admin:
            Group = True
        else:
            Group = None
        playty = await get_playtype(CallbackQuery.message.chat.id)
        if playty == "Everyone":
            Playtype = False
        else:
            Playtype = True
        buttons = playmode_users_markup(_, Direct, Group, Playtype)
    if command == "PLAYTYPECHANGE":
        try:
            await CallbackQuery.answer(_["set_cb_3"], show_alert=True)
        except:
            pass
        playty = await get_playtype(CallbackQuery.message.chat.id)
        if playty == "Everyone":
            await set_playtype(CallbackQuery.message.chat.id, "Admin")
            Playtype = False
        else:
            await set_playtype(CallbackQuery.message.chat.id, "Everyone")
            Playtype = True
        playmode = await get_playmode(CallbackQuery.message.chat.id)
        if playmode == "Direct":
            Direct = True
        else:
            Direct = None
        is_non_admin = await is_nonadmin_chat(CallbackQuery.message.chat.id)
        if not is_non_admin:
            Group = True
        else:
            Group = None
        buttons = playmode_users_markup(_, Direct, Group, Playtype)
    try:
        return await CallbackQuery.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except MessageNotModified:
        return


@app.on_callback_query(filters.regex(pattern=r"^(AUTH|AUTHLIST)$") & ~BANNED_USERS)
@ActualAdminCB
async def authusers_mar(client, CallbackQuery, _):
    command = CallbackQuery.matches[0].group(1)
    if command == "AUTHLIST":
        _authusers = await get_authuser_names(CallbackQuery.message.chat.id)
        if not _authusers:
            try:
                return await CallbackQuery.answer(_["setting_4"], show_alert=True)
            except:
                return
        else:
            try:
                await CallbackQuery.answer(_["set_cb_4"], show_alert=True)
            except:
                pass
            j = 0
            await CallbackQuery.edit_message_text(_["auth_6"])
            msg = _["auth_7"].format(CallbackQuery.message.chat.title)
            for note in _authusers:
                _note = await get_authuser(CallbackQuery.message.chat.id, note)
                user_id = _note["auth_user_id"]
                admin_id = _note["admin_id"]
                admin_name = _note["admin_name"]
                try:
                    user = await app.get_users(user_id)
                    user = user.first_name
                    j += 1
                except:
                    continue
                msg += f"{j}➤ {user}[<code>{user_id}</code>]\n"
                msg += f"   {_['auth_8']} {admin_name}[<code>{admin_id}</code>]\n\n"
            upl = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=_["BACK_BUTTON"], callback_data=f"AU"
                        ),
                        InlineKeyboardButton(
                            text=_["CLOSE_BUTTON"],
                            callback_data=f"close",
                        ),
                    ]
                ]
            )
            try:
                return await CallbackQuery.edit_message_text(msg, reply_markup=upl)
            except MessageNotModified:
                return
    try:
        await CallbackQuery.answer(_["set_cb_3"], show_alert=True)
    except:
        pass
    if command == "AUTH":
        is_non_admin = await is_nonadmin_chat(CallbackQuery.message.chat.id)
        if not is_non_admin:
            await add_nonadmin_chat(CallbackQuery.message.chat.id)
            buttons = auth_users_markup(_)
        else:
            await remove_nonadmin_chat(CallbackQuery.message.chat.id)
            buttons = auth_users_markup(_, True)
    try:
        return await CallbackQuery.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except MessageNotModified:
        return


@app.on_callback_query(filters.regex("VOMODECHANGE") & ~BANNED_USERS)
@ActualAdminCB
async def vote_change(client, CallbackQuery, _):
    command = CallbackQuery.matches[0].group(1)
    try:
        await CallbackQuery.answer(_["set_cb_3"], show_alert=True)
    except:
        pass
    mod = None
    if await is_skipmode(CallbackQuery.message.chat.id):
        await skip_off(CallbackQuery.message.chat.id)
    else:
        mod = True
        await skip_on(CallbackQuery.message.chat.id)
    current = await get_upvote_count(CallbackQuery.message.chat.id)
    buttons = vote_mode_markup(_, current, mod)

    try:
        return await CallbackQuery.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except MessageNotModified:
        return






from datetime import datetime

@app.on_callback_query(filters.regex("rishuuuuuuu"))
@languageCB
async def suupport(client, CallbackQuery, _):

    bot = await client.get_me()
    bot_mention = f'<a href="https://t.me/{bot.username}">{bot.first_name}</a>'

    last_updated = datetime.utcnow().strftime("%d %B %Y")

    text = f"""<b><tg-emoji emoji-id=6195245116207143870>🔒</tg-emoji> ᴘʀɪᴠᴀᴄʏ ᴘᴏʟɪᴄʏ — {bot_mention}

ʟᴀsᴛ ᴜᴘᴅᴀᴛᴇᴅ : <code> {last_updated} </code>

<tg-emoji emoji-id=5364066964727678118>💱</tg-emoji> ɪɴғᴏʀᴍᴀᴛɪᴏɴ ᴡᴇ ᴄᴏʟʟᴇᴄᴛ :
• ᴜsᴇʀ ɪᴅ | ᴄʜᴀᴛ ɪᴅ  
• ᴜsᴇʀɴᴀᴍᴇ (__ɪғ ᴀᴠᴀɪʟᴀʙʟᴇ__)

<tg-emoji emoji-id=5039727604517570274>🌕</tg-emoji> ᴅᴀᴛᴀ ᴜsᴀɢᴇ :
• ᴍᴜsɪᴄ sᴛʀᴇᴀᴍɪɴɢ & ᴘʟᴀʏʙᴀᴄᴋ  
• ᴘʟᴀʏʟɪsᴛ ᴀɴᴅ ᴘʀᴇғᴇʀᴇɴᴄᴇ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ  
• ʙᴏᴛ ᴘᴇʀғᴏʀᴍᴀɴᴄᴇ ᴀɴᴅ sᴛᴀʙɪʟɪᴛʏ  
• sᴇʀᴠɪᴄᴇ-ʀᴇʟᴀᴛᴇᴅ ɴᴏᴛɪғɪᴄᴀᴛ+ɪᴏɴs </b>.
<blockquote expandable>
<b>
<tg-emoji emoji-id=5197288647275071607>🛡</tg-emoji> ᴅᴀᴛᴀ ᴘʀᴏᴛᴇᴄᴛɪᴏɴ :
• ᴡᴇ ᴅᴏ ɴᴏᴛ sᴛᴏʀᴇ ᴘᴇʀsᴏɴᴀʟ ᴍᴇssᴀɢᴇs  
• ᴡᴇ ᴅᴏ ɴᴏᴛ sᴛᴏʀᴇ ᴍᴇᴅɪᴀ ғɪʟᴇs  
• ᴡᴇ ᴅᴏ ɴᴏᴛ sʜᴀʀᴇ ᴅᴀᴛᴀ ᴡɪᴛʜ ᴛʜɪʀᴅ ᴘᴀʀᴛɪᴇs  
• ᴡᴇ ᴅᴏ ɴᴏᴛ ᴜsᴇ ᴅᴀᴛᴀ ғᴏʀ ᴀᴅs ᴏʀ ᴘʀᴏᴍᴏᴛɪᴏɴ's  

<tg-emoji emoji-id=5332586662629227075>🗂</tg-emoji> ᴅᴀᴛᴀ ʀᴇᴛᴇɴᴛɪᴏɴ :
• ᴅᴀᴛᴀ ɪs sᴛᴏʀᴇᴅ ᴏɴʟʏ ғᴏʀ sᴇʀᴠɪᴄᴇ ғᴜɴᴄᴛɪᴏɴᴀʟɪᴛʏ  
• ᴅᴀᴛᴀ ᴄᴀɴ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ᴏɴ ᴜsᴇʀ ʀᴇǫᴜᴇsᴛ    

<tg-emoji emoji-id=5989975649740134220>📝</tg-emoji> ɴᴏᴛᴇ's :
• ᴜsɪɴɢ ᴛʜɪs ʙᴏᴛ ᴍᴇᴀɴs ʏᴏᴜ ᴀɢʀᴇᴇ ᴛᴏ ᴛʜɪs ᴘᴏʟɪᴄʏ    
• ʙᴀsɪᴄ ᴅᴀᴛᴀ sᴛᴏʀᴀɢᴇ ɪs ʀᴇǫᴜɪʀᴇᴅ ғᴏʀ ʙᴏᴛ ᴡᴏʀᴋɪɴɢ</b></blockquote>"""

    await CallbackQuery.edit_message_text(
        text=text,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("ʙᴀᴄᴋ", callback_data="settingsback_helper",icon_custom_emoji_id=5416117059207572332,
                style=ButtonStyle.DANGER,)
                ],
            ]
        ),
    )



@app.on_callback_query(filters.regex("riiiiishuuuuuuuuuuu"))
@languageCB
async def supportuvh(client, CallbackQuery, _):
    try:
        await CallbackQuery.answer()
    except:
        pass

    bot = await client.get_me()
    bot_mention = f'<a href="https://t.me/{bot.username}">{bot.first_name}</a>'

    text = f"""<blockquote expandable><b><tg-emoji emoji-id=5424729550967807644>🎧</tg-emoji> {bot_mention}</b>

<b><tg-emoji emoji-id=5467538555158943525>💭</tg-emoji>ɪs ᴀ ᴘᴏᴡᴇʀғᴜʟ ᴀɴᴅ ʜɪɢʜ-ᴘᴇʀғᴏʀᴍᴀɴᴄᴇ ᴛᴇʟᴇɢʀᴀᴍ ᴍᴜsɪᴄ ʙᴏᴛ 
ᴅᴇsɪɢɴᴇᴅ ᴛᴏ ᴅᴇʟɪᴠᴇʀ ᴄʀʏsᴛᴀʟ-ᴄʟᴇᴀʀ ᴀᴜᴅɪᴏ sᴛʀᴇᴀᴍɪɴɢ 
ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛs ᴡɪᴛʜ ᴇᴀsᴇ.</b>

<b>ᴇɴᴊᴏʏ sᴍᴏᴏᴛʜ ᴘʟᴀʏʙᴀᴄᴋ, ᴀᴅᴠᴀɴᴄᴇᴅ ᴄᴏɴᴛʀᴏʟs 
ᴀɴᴅ ᴀ ᴘʀᴇᴍɪᴜᴍ ᴍᴜsɪᴄ ᴇxᴘᴇʀɪᴇɴᴄᴇ <tg-emoji emoji-id=5224607267797606837>☄️</tg-emoji></b></blockquote>

<b>❖ ʙᴏᴛ ғᴜʟʟ ɪɴғᴏ :</b>
<b>├<tg-emoji emoji-id=5990276318925691338>⚡️</tg-emoji> ᴠᴇʀsɪᴏɴ :</b>  <code> 5.1.1</code>
<b>├<tg-emoji emoji-id=5319161050128459957>👨‍💻</tg-emoji> ᴅᴇᴠᴇʟᴏᴘᴇʀ : </b> <a href="https://t.me/Rishu1286">ʀɪsʜᴜ</a>  
<b>├<tg-emoji emoji-id=6021418126061605425>📢</tg-emoji> ᴜᴘᴅᴀᴛᴇ :</b> <a href="https://t.me/+R0MFX0nSjRZiYTBl">ᴄʜᴀɴɴᴇʟ</a>  
<b>├<tg-emoji emoji-id=5462956611033117422>📀</tg-emoji> ᴅᴀᴛᴀʙᴀꜱᴇ :</b><code> MongoDB  </code>
<b>├<tg-emoji emoji-id=6025871229758476400>💻</tg-emoji> sᴇʀᴠᴇʀ :</b> <code>Virtual Private Server</code>
<b>├<tg-emoji emoji-id=5041992177563993101>☄️</tg-emoji> ᴘᴏᴡᴇʀᴇᴅ :</b> <a href="https://t.me/aboutanuragxanu">ʏᴏᴜᴛᴜʙᴇ</a>  
<b>╰<tg-emoji emoji-id=5989975649740134220>📝</tg-emoji> ʟᴀɴɢᴜᴀɢᴇ :</b><code> Python </code>| <code>Py-TgCalls </code>| <code>Pyrogram  </code>

<b><tg-emoji emoji-id=5039928501612839813>🟢</tg-emoji>ᴏɴʟɪɴᴇ :</b><code> {datetime.utcnow().strftime("%d %B %Y")}</code>

<b><tg-emoji emoji-id=5042328396193864923>🛡</tg-emoji> ᴘʀɪᴠᴀᴄʏ :</b>
<b>ɪꜰ ʏᴏᴜ ᴜꜱᴇ {bot_mention}, ʏᴏᴜ ᴀɢʀᴇᴇ ᴛᴏ
ᴘᴏʟɪᴄʏ ᴄᴀɴ ʙᴇ ᴜᴘᴅᴀᴛᴇᴅ ᴀɴʏᴛɪᴍᴇ.</b>
"""

    buttons = InlineKeyboardMarkup(
        [
            
            [
                InlineKeyboardButton("ʙᴀᴄᴋ", callback_data="settingsback_helper",icon_custom_emoji_id=5416117059207572332,
                style=ButtonStyle.DANGER,)
            ],
        ]
    )

    # ✅ Safe edit (no caption error)
    try:
        await CallbackQuery.edit_message_text(
            text=text,
            reply_markup=buttons,
            disable_web_page_preview=True
        )
    except:
        await CallbackQuery.message.delete()
        await client.send_message(
            CallbackQuery.message.chat.id,
            text,
            reply_markup=buttons,
            disable_web_page_preview=True
        )




@app.on_callback_query(filters.regex("Khushi") & ~BANNED_USERS)
@languageCB
async def support(client, CallbackQuery, _):
    await CallbackQuery.edit_message_text(
        _["ABOUT_1"].format(app.mention),
        reply_markup=InlineKeyboardMarkup(
            [
                [          
                    InlineKeyboardButton(
                        text=" σᴡηєʀ ", user_id=config.OWNER_ID,icon_custom_emoji_id=5217822164362739968,
                style=ButtonStyle.SUCCESS,
                    ),
                    
                ],
                [
                    InlineKeyboardButton(
                        text="sυᴘᴘσʀᴛ", url=config.SUPPORT_CHAT,icon_custom_emoji_id=5282843764451195532,
                style=ButtonStyle.PRIMARY,
                    ),
                    InlineKeyboardButton(
                        text="υᴘᴅᴧᴛєs", url=config.SUPPORT_CHANNEL,icon_custom_emoji_id=5253742260054409879,
                style=ButtonStyle.SUCCESS,
                    ),

                ],
                [          
                    InlineKeyboardButton(
                        text="ʙᴧᴄᴋ", callback_data=f"settingsback_helper",icon_custom_emoji_id=5416117059207572332,
                style=ButtonStyle.DANGER,
                    )
                ],
            ]
        ),
    )




@app.on_callback_query(filters.regex("^api_status$"))
async def show_bot_info(c: app, q: CallbackQuery):
    start = time()
    x = await c.send_message(q.message.chat.id, "ᴘɪɴɢ ᴘᴏɴɢ 💘..")
    delta_ping = time() - start
    await x.delete()

    txt = f"""📼 ᴘɪɴɢ ᴘᴏɴɢ ʙᴀʙʏ...

• ᴅᴀᴛᴀʙᴀsᴇ: ᴏɴʟɪɴᴇ
• ʏᴏᴜᴛᴜʙᴇ ᴀᴘɪ: ʀᴇsᴘᴏɴsɪᴠᴇ
• ʙᴏᴛ sᴇʀᴠᴇʀ: ʀᴜɴɴɪɴɢ sᴍᴏᴏᴛʜʟʏ
• ʀᴇsᴘᴏɴsᴇ ᴛɪᴍᴇ: ᴏᴘᴛɪᴍᴀʟ
• ᴀᴘɪ ᴘɪɴɢ: {delta_ping * 1000:.3f} ms   

• ᴇᴠᴇʀʏᴛʜɪɴɢ ʟᴏᴏᴋs ɢᴏᴏᴅ!
"""
    await q.answer(txt, show_alert=True)

