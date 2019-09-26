#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import json
import fcntl
import shutil
import subprocess
import random
import time

from flask import Flask, Request, jsonify, request, send_file
from tempfile import mkstemp
import redis

from mpd import MPDClient, CommandError

app = Flask(__name__, static_folder='/static')
app.config.from_object('default_config')
if 'RADIO_CONFIG' in os.environ:
    app.config.from_envvar('RADIO_CONFIG')

app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True
app.jinja_env.line_statement_prefix = '#'


class TempFile(object):
    def __init__(self, filename):
        self.fd, self.path = mkstemp()
        self.file = os.fdopen(self.fd, 'w+b')
        self.filename = filename
    
    def tell(self):
        return self.file.tell()
    
    def read(self, size=-1):
        return self.file.read(size)
    
    def seek(self, offset, whence=0):
        return self.file.seek(offset, whence)
    
    @property
    def name(self):
        if self.filename is not None:
            return self.filename
        else:
            return self.file.name
    
    def write(self, data):
        return self.file.write(data)
    
    def truncate(self, size=None):
        return self.file.truncate(size)
    
    def flush(self):
        return self.file.flush(size)
    
    def fileno(self):
        return self.file.fileno()
    
    def close(self):
        try:
            os.remove(self.path)
        except: pass
        try:
            self.file.close()
        except: pass

class MyRequest(Request):
    def _get_file_stream(self, total_content_length, content_type, filename=None, content_length=None):
        return TempFile(filename)
app.request_class = MyRequest

def random_string(n, characters='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
    return ''.join(random.choice(characters) for _ in range(n))

def mutagen_format(src, original=None):
    import mutagen
    f = mutagen.File(src, easy=True)
    
    if f is not None:
        title = f.get('title')
        artist = f.get('artist')
        album = f.get('album')
        tracknumber = f.get('tracknumber')
        extension = os.path.splitext(original if original is not None else src)[1]
        
        # only format if title is defined
        if title is not None:
            name = ''
            if artist       is not None: name += '{} - '.format(', '.join(artist))
            if album        is not None: name += '{} - '.format(', '.join(album))
            if tracknumber  is not None: name += '{:0>2} '.format(tracknumber[0].split('/')[0])
            name += ', '.join(title)
            
            max_length = 200
            if len(name) > max_length:
                name = name[:max_length]
            
            # TODO do this correctly
            name = name.replace('/', '_').replace('\\', '_')
            
            return name + extension
    
    return None


def redis_connect():
    host = app.config.get('REDIS_HOST', 'localhost')
    port = app.config.get('REDIS_PORT', 6379)
    return redis.Redis(host=host, port=port, db=0, decode_responses=True)

def redis_set(key, value):
    key_prefix = app.config.get('REDIS_PREFIX', 'radio') + '--'
    key = key_prefix + key
    r = redis_connect()
    return r.set(key, value)

def redis_get(key):
    key_prefix = app.config.get('REDIS_PREFIX', 'radio') + '--'
    key = key_prefix + key
    r = redis_connect()
    return r.get(key)

def redis_delete(key):
    key_prefix = app.config.get('REDIS_PREFIX', 'radio') + '--'
    key = key_prefix + key
    r = redis_connect()
    with r.pipeline() as pipe:
        pipe.get(key)
        pipe.delete(key)
        return pipe.execute()[0]


def mpd_connect():
    mpd = MPDClient()
    mpd.connect(host=app.config.get('MPD_HOST'), port=app.config.get('MPD_PORT'))
    mpd.iterate = True
    pw = app.config.get('MPD_PASSWORD', None)
    if pw is not None:
        mpd.password(pw)
    return mpd

def mpd_request(mpd, file):
    playlist = list(mpd.playlist())
    mpd.addid(file, len(playlist) - app.config.get('PLAYLIST_BUFFER', 0))

def process_tags(song):
    song.pop('last-modified', None)
    song.pop('pos', None)
    song.pop('id', None)
    
    for tag, value in song.items():
       if isinstance(value, list):
            song[tag] = ', '.join(set(value))
    
    filename = os.path.basename(song['file'])
    song['thumb'] = '/api/thumb/{}.jpg'.format(filename)
    
    return song

# replace with a search function
def mpd_info():
    mpd = mpd_connect()
    status = mpd.status()
    plist = mpd.playlistinfo()
    info = {
        'status': {
            'state': status['state'],
            'song': status['song'], # id in playlist
            'elapsed': status['elapsed']
        },
        'playlist': [process_tags(t) for t in plist]
    }
    mpd.disconnect()
    
    return info


@app.route('/api/upload', methods=['POST'])
def upload_song():
    if not app.config.get('UPLOADS_ENABLED', False):
        return app.response_class(
            response='{"error":"uploads are disabled"}',
            status=403,
            mimetype='application/json'
        )
    
    file = request.files.get('file', None)
    if file is None or file.filename == '':
        return app.response_class(
            response='{"error":"no file uploaded"}',
            status=400,
            mimetype='application/json'
        )
    
    src = file.stream.path
    
    upload_path = app.config.get('MUSIC_FOLDER')
    
    base = os.path.basename(file.filename)
    if app.config.get('RENAME_FILES', False):
        name = mutagen_format(src, base)
        
        if name is None:
            name = base
        
    else:
        name = base
    
    dst = os.path.join(upload_path, name)
    
    # TODO convert to opus with ffmpeg
    
    if os.path.exists(dst):
        return app.response_class(
            response='{"error":"file already exists on the server"}',
            status=409,
            mimetype='application/json'
        )
    
    shutil.move(src, dst)
    os.chmod(dst, 0o644)
    
    mpd = mpd_connect()
    mpd.update()
    
    subsystem = []
    while 'database' not in subsystem:
        mpd.send_idle()
        subsystem = list(mpd.fetch_idle())
    
    # get info on the new song
    results = list(mpd.find('file', name))
    
    mpd.disconnect()
    
    response = {}
    
    if len(results) > 0:
        song = process_tags(results[0])
        
        if app.config.get('REQUESTS_ENABLED', False):
            token = random_string(10)
            timelimit = int(time.time()) + app.config.get('REQUEST_TIMEOUT', 300)
            redis_set(token, '{}/{}'.format(song['file'], timelimit))
            song['token'] = token
        
        response['song'] = song
    
    return app.response_class(
        response=json.dumps(response),
        status=200,
        mimetype='application/json'
    )

@app.route('/api/request/<token>', methods=['GET'])
def request_song(token):
    if not app.config.get('REQUESTS_ENABLED', False):
        return app.response_class(status=404)
    
    t = redis_delete(token)
    
    if t is not None:
        filename, limit = t.rsplit('/', 1)
        
        if int(time.time()) < int(limit):
            mpd = mpd_connect()
            mpd_request(mpd, filename)
            mpd.disconnect()
    
    return app.response_class(status=200)

"""
@app.route('/api/list', methods=['GET'])
def list_files():
    mpd = mpd_connect()
    
    files = set()
    for track in self.mpd.listall():
        if 'file' in track:
            files.add(track['file'])
    
    mpd.disconnect()
    
    return app.response_class(
        response=json.dumps(files),
        status=200,
        mimetype='application/json'
    )
"""

@app.route('/api/info', methods=['GET'])
def info():
    return app.response_class(
        response=json.dumps(mpd_info()),
        status=200,
        mimetype='application/json'
    )

@app.route('/api/info/<filename>', methods=['GET'])
def song_info(filename):
    mpd = mpd_connect()
    results = list(mpd.find('file', filename))
    mpd.disconnect()
    
    if len(results) == 0:
        return app.response_class(
            response='{"error": "song not found"}',
            status=404,
            mimetype='application/json'
        )
    
    return app.response_class(
        response=json.dumps(process_tags(results[0])),
        status=200,
        mimetype='application/json'
    )



@app.route('/api/config', methods=['GET'], defaults={'ext': ''})
@app.route('/api/config<ext>', methods=['GET'])
def config(ext):
    return app.response_class(
        response=json.dumps({
            'WEBSITE_TITLE': app.config.get('WEBSITE_TITLE'),
            'API_ENDPOINT': app.config.get('API_ENDPOINT'),
            'AUDIO_SOURCE': app.config.get('AUDIO_SOURCE'),
            'UPLOADS_ENABLED': app.config.get('UPLOADS_ENABLED'),
            'CONCURRENT_UPLOADS': app.config.get('CONCURRENT_UPLOADS'),
            'EXTRA_LINKS': app.config.get('EXTRA_LINKS')
        }),
        status=200,
        mimetype='application/json'
    )

@app.route('/api/thumb/<filename>.jpg', methods=['GET'])
def thumbnail(filename):
    path = app.config.get('MUSIC_FOLDER')
    input = '{}/{}'.format(path, filename)
    
    thumbs_path = app.config.get('THUMBS_FOLDER')
    output = '{}/{}.jpg'.format(thumbs_path, filename)
    
    out = open(output, 'ab+')
    fcntl.flock(out.fileno(), fcntl.LOCK_EX)
    out.seek(0, os.SEEK_END)
    
    size = out.tell()
    if size == 0:
        thumb_largest_side = 250
        
        ffmpeg = app.config.get('FFMPEG', None)
        if ffmpeg is None:
            ffmpeg = 'ffmpeg'
        
        # ffmpeg -i $input -an -c:v mjpeg -vf scale=w=$max_size:h=$max_size:force_original_aspect_ratio=decrease -f mjpeg -
        FNULL = open(os.devnull, 'w')
        process = subprocess.Popen([
            ffmpeg, '-y', '-nostats', '-loglevel', 'error', 
            '-i', input,
            '-c:v', 'mjpeg',
            '-an', '-sn',
            '-vf', 'scale=w={0}:h={0}:force_original_aspect_ratio=decrease'.format(thumb_largest_side),
            '-f', 'mjpeg',
            '-'
        ], shell=False, stdout=out, stderr=FNULL)
        process.wait()
        
        if process.returncode != 0:
            out.seek(0)
            out.truncate(0)
            out.write(b'\x00')
    
    out.close()
    
    return send_file(output)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8088)
