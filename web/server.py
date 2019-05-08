#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import json
import fcntl
import shutil
import subprocess

from flask import Flask, Request, jsonify, request, send_file
from tempfile import mkstemp

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


def mpd_connect():
    mpd = MPDClient()
    mpd.connect(host=app.config.get('MPD_HOST'), port=app.config.get('MPD_PORT'))
    mpd.iterate = True
    pw = app.config.get('MPD_PASSWORD', None)
    if pw is not None:
        mpd.password(pw)
    return mpd

def process_tags(song):
    del song['last-modified']
    del song['pos']
    del song['id']
    
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
    
    upload_path = app.config.get('MUSIC_FOLDER')
    name = os.path.basename(file.filename)
    
    # TODO convert to opus with ffmpeg
    # TODO rename file with mutagen
    
    dst = os.path.join(upload_path, name)
    if os.path.exists(dst):
        return app.response_class(
            response='{"error":"file already exists on the server"}',
            status=403,
            mimetype='application/json'
        )
    
    src = file.stream.path
    
    shutil.move(src, dst)
    os.chmod(dst, 0o644)
    
    mpd = mpd_connect()
    mpd.update()
    
    subsystem = []
    while 'database' not in subsystem:
        mpd.send_idle()
        subsystem = list(mpd.fetch_idle())
    
    # get info on the new song
    results = mpd.find('file', file.filename)
    
    mpd.disconnect()
    
    # TODO remove this and the verification
    response = {'success': True}
    
    if len(results) > 0:
        response['song'] = process_tags(results[0])
    
    return app.response_class(
        response=json.dumps(response),
        status=200,
        mimetype='application/json'
    )

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
def song_info():
    mpd = mpd_connect()
    results = mpd.find('file', file.filename)
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
    out.seek(0)
    
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
