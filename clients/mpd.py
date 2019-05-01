# -*- coding: utf-8 -*-
import mpd

class MpdCommand(object):
    def __init__(self, conn, command):
        self._conn = conn
        self._command = command
    
    def __call__(self, *args, **kwargs):
        try:
            self._conn.ping()
        except:
            self._conn.reconnect()
        
        return self._command(*args, **kwargs)

class MpdConnection(object):
    def __init__(self, host, port, password=None, iterate=False):
        self.host = host
        self.port = port
        # why
        self.password = password
        self.iterate = iterate
        
        self._mpd = mpd.MPDClient()
        self.reconnect()
        
    def reconnect(self):
        if self._mpd is not None:
            try:
                self._mpd.disconnect()
            except: pass
        
        self._mpd.connect(host=self.host, port=self.port)
        self._mpd.iterate = self.iterate
        if self.password is not None:
            self._mpd.password(self.password)
    
    def ping(self, *args, **kwargs):
        return self._mpd.ping(*args, **kwargs)
    
    def disconnect(self, *args, **kwargs):
        return self._mpd.disconnect(*args, **kwargs)
    
    def __getattr__(self, name):
        value = getattr(self._mpd, name)
        if callable(value):
            return MpdCommand(self, value)
        else:
            return value
    
    def __dir__(self):
        return dir(self._mpd)
    
    def __repr__(self):
        return self._mpd.__repr__()

class SongInfo(object):
    def __init__(self, info, elapsed=None):
        self.info = self._collapse_tags(info)
        self.file = self.info['file']
        self.filename = self.file[self.file.rindex('/') + 1:]
        
        self.title = self.info.get('title', self.filename)
        self.artist = self.info.get('artist', None)
        self.album = self.info.get('album', None)
        
        self.time = int(self.info['time'])
        self.time_str = self._sec_to_time(self.time)
        
        if elapsed is not None:
            self.elapsed = int(float(elapsed))
            self.elapsed_str = self._sec_to_time(self.elapsed)
        else:
            self.elapsed = None
            self.elapsed_str = ''
    
    @staticmethod
    def _sec_to_time(seconds):
        return '{}:{:02}'.format(seconds // 60, seconds % 60)
    
    @staticmethod
    def _collapse_tags(song):
        for tag, value in song.items():
           if isinstance(value, list):
                song[tag] = ', '.join(set(value))
        return song
    
    def __str__(self):
        ss = self.title
        if self.artist is not None:
            ss += ' | ' + self.artist
        
        if self.album is not None:
            ss += ' | ' + self.album
        
        ss += ' | '
        
        if self.elapsed is not None:
            ss += self.elapsed_str + '/'
        
        ss += self.time_str
        
        return ss
    
    def __eq__(self, other):
        return isinstance(other, SongInfo) and self.file == other.file

