DEBUG = True
SECRET_KEY = 'debug'

MPD_HOST = '127.0.0.1'
MPD_PORT = 6600

# defaults to 'ffmpeg' if None
FFMPEG = None

MUSIC_FOLDER = None
THUMBS_FOLDER = None

# client config
WEBSITE_NAME = 'radio'
API_ENDPOINT = 'http://localhost' # /api/<method> is appended on top of this
AUDIO_SOURCE = 'http://localhost:8000/stream.mp3'
CONCURRENT_UPLOADS = 1
EXTRA_LINKS = [
    # (label:str, url:str, newtab:bool, download:bool)
    ('direct stream', AUDIO_SOURCE, True, False)
]

