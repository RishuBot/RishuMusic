from RishuMusic.core.bot import Shree as shree
from RishuMusic.core.dir import dirr
from RishuMusic.core.git import git
from RishuMusic.core.userbot import Userbot
from RishuMusic.misc import dbb, heroku

from .logging import LOGGER

dirr()
git()
dbb()
heroku()

app = shree()
userbot = Userbot()

# Rich Message + premium-emoji auto-upgrade — applied once, right after the
# Client exists, before any plugin imports run. Order matters: rich patch
# first, emoji patch second (see each module's own docstring for why).
from RishuMusic.utils.rich_patch import apply_rich_patch
from RishuMusic.utils.premium_emojis import apply_emoji_patch

apply_rich_patch()
apply_emoji_patch()

from .platforms import *

Apple = AppleAPI()
Carbon = CarbonAPI()
SoundCloud = SoundAPI()
Spotify = SpotifyAPI()
Resso = RessoAPI()
Telegram = TeleAPI()
YouTube = YouTubeAPI()
