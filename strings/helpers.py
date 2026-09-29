# strings/helpers.py — rich <table> version.
# REQUIRES utils/rich_ui.py to be deployed and apply_rich_patch() called at
# startup (utils/rich_patch.py) — the plugin code sends these via plain
# edit_message_text()/reply_text() calls, and the patch is what auto-
# upgrades a <table>-containing string into a real Bot API rich message.
# Without the patch active, these render broken/empty.
#
# Emoji below are plain Unicode on purpose — rich_ui.py's rich send/edit
# path auto-upgrades them to premium <tg-emoji> tags if premium_emojis.py
# is installed; otherwise they just stay normal emoji.

from RishuMusic.utils.rich_ui import rich_table, rich_heading, rich_note

HELP_1 = (
    rich_heading("🛡️ ADMIN COMMANDS", level=2)
    + rich_note("Prefix any command below with <b>c</b> to use it for a channel (e.g. <code>/cpause</code>).")
    + rich_table(
        ["Command", "Description"],
        [
            ("<code>/pause</code>", "Pause the current playing stream"),
            ("<code>/resume</code>", "Resume the paused stream"),
            ("<code>/skip</code>", "Skip the current track, play the next in queue"),
            ("<code>/end</code> or <code>/stop</code>", "Clear the queue and end the current stream"),
            ("<code>/player</code>", "Get an interactive player panel"),
            ("<code>/queue</code>", "Show the queued tracks list"),
        ],
    )
)

HELP_2 = (
    rich_heading("🔑 AUTH USERS", level=2)
    + rich_note("Auth users can use admin rights in the bot without needing admin rights in the chat.")
    + rich_table(
        ["Command", "Description"],
        [
            ("<code>/auth</code> [username/id]", "Add a user to the auth list"),
            ("<code>/unauth</code> [username/id]", "Remove a user from the auth list"),
            ("<code>/authusers</code>", "Show the list of auth users"),
        ],
    )
)

HELP_3 = (
    rich_heading("📢 BROADCAST", level=2)
    + rich_note("Only for sudoers. <code>/broadcast</code> [message or reply] — send a message to every served chat.")
    + rich_table(
        ["Mode", "Effect"],
        [
            ("<code>-pin</code>", "Pins the broadcasted message in served chats"),
            ("<code>-pinloud</code>", "Pins it and notifies members"),
            ("<code>-user</code>", "Sends to users who started the bot"),
            ("<code>-assistant</code>", "Sends from the bot's assistant account"),
            ("<code>-nobot</code>", "Skips broadcasting from the bot itself"),
        ],
    )
    + rich_note("<b>Example:</b> <code>/broadcast -user -assistant -pin testing broadcast</code>")
)

HELP_4 = (
    rich_heading("🚫 CHAT BLACKLIST", level=2)
    + rich_note("Only for sudoers. Restrict specific chats from using the bot.")
    + rich_table(
        ["Command", "Description"],
        [
            ("<code>/blacklistchat</code> [chat id]", "Blacklist a chat from using the bot"),
            ("<code>/whitelistchat</code> [chat id]", "Whitelist a blacklisted chat"),
            ("<code>/blacklistedchat</code>", "Show the list of blacklisted chats"),
        ],
    )
)

HELP_5 = (
    rich_heading("⛔ BLOCK USERS", level=2)
    + rich_note("Only for sudoers. A blocked user is ignored and can't use bot commands.")
    + rich_table(
        ["Command", "Description"],
        [
            ("<code>/block</code> [username or reply]", "Block a user from the bot"),
            ("<code>/unblock</code> [username or reply]", "Unblock the blocked user"),
            ("<code>/blockedusers</code>", "Show the list of blocked users"),
        ],
    )
)

HELP_6 = (
    rich_heading("📡 CHANNEL PLAY", level=2)
    + rich_note("Stream audio/video directly in a channel's voice chat.")
    + rich_table(
        ["Command", "Description"],
        [
            ("<code>/cplay</code>", "Stream the requested audio track in the channel's voice chat"),
            ("<code>/cvplay</code>", "Stream the requested video track in the channel's voice chat"),
            ("<code>/cplayforce</code> / <code>/cvplayforce</code>", "Stop the current stream and force-play the requested track"),
            ("<code>/channelplay</code> [chat username/id] or [disable]", "Connect a channel to a group so its commands control the stream"),
        ],
    )
)

HELP_7 = (
    rich_heading("🌐 GLOBAL BAN", level=2)
    + rich_note("Only for sudoers.")
    + rich_table(
        ["Command", "Description"],
        [
            ("<code>/gban</code> [username or reply]", "Globally ban the user from every served chat and blacklist them from the bot"),
            ("<code>/ungban</code> [username or reply]", "Globally unban the user"),
            ("<code>/gbannedusers</code>", "Show the list of globally banned users"),
        ],
    )
)

HELP_8 = (
    rich_heading("🔁 LOOP STREAM", level=2)
    + rich_note("Keep the ongoing stream repeating.")
    + rich_table(
        ["Command", "Description"],
        [
            ("<code>/loop</code> [enable/disable]", "Enable or disable loop for the ongoing stream"),
            ("<code>/loop</code> [1, 2, 3, ...]", "Enable loop for the given number of repeats"),
        ],
    )
)

HELP_9 = (
    rich_heading("🛠️ MAINTENANCE MODE", level=2)
    + rich_note("Only for sudoers.")
    + rich_table(
        ["Command", "Description"],
        [
            ("<code>/logs</code>", "Get the bot's logs"),
            ("<code>/logger</code> [enable/disable]", "Start/stop logging bot activity"),
            ("<code>/maintenance</code> [enable/disable]", "Enable or disable maintenance mode"),
        ],
    )
)

HELP_10 = (
    rich_heading("🤖 AI FEATURES", level=2)
    + rich_table(
        ["Command", "Description"],
        [
            ("<code>/ai</code>", "Chat with the AI"),
            ("<code>/tts</code>", "Convert your message into natural-sounding voice"),
            ("<code>/image</code>", "Describe what you want and the AI generates an image"),
        ],
    )
)
