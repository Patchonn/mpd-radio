DEBUG = True
SECRET_KEY = 'debug'

MPD_HOST = '127.0.0.1'
MPD_PORT = 6600

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_PREFIX = 'radio'
REQUEST_TIMEOUT = 300

# defaults to 'ffmpeg' if None
FFMPEG = None

MUSIC_FOLDER = None
THUMBS_FOLDER = None


UPLOADS_ENABLED = False

# client config
WEBSITE_NAME = 'radio'
API_ENDPOINT = 'http://localhost' # /api/<method> is appended on top of this
AUDIO_SOURCE = 'http://localhost:8000/stream.mp3'
CONCURRENT_UPLOADS = 1
EXTRA_LINKS = [
    # (label:str, url:str, newtab:bool, download:bool)
    ('direct stream', AUDIO_SOURCE, True, False)
]

# TODO
PLAYLIST_BUFFER = 3

