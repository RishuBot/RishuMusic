from shreeMusic.core.bot import shree
from shreeMusic.core.dir import dirr
from shreeMusic.core.git import git
from shreeMusic.core.userbot import Userbot
from shreeMusic.misc import dbb, heroku

from .logging import LOGGER

dirr()
git()
dbb()
heroku()

app = shree()
userbot = Userbot()

from .platforms import *

Apple = AppleAPI()
Carbon = CarbonAPI()
SoundCloud = SoundAPI()
Spotify = SpotifyAPI()
Resso = RessoAPI()
Telegram = TeleAPI()
YouTube = YouTubeAPI()
