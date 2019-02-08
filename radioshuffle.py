#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import random

import common
from mpd import MPDClient, CommandError

config = common.get_config('MPD_RADIO_CONFIG')
logger = common.get_logger('bot', level=config.LOG_LEVEL)

class mpdshuffle(object):
    def __init__(self, mpd, buffer, window_size):
        self.mpd = mpd
        self.buffer = buffer
        self.window_size = window_size
    
    def _tracks(self):
        tracks = set()
        for track in self.mpd.listall():
            if 'file' in track:
                tracks.add(track['file'])
        return tracks
    
    def _playlist(self):
        playlist = []
        for track in self.mpd.playlistinfo():
            playlist.append(track['file'])
        return playlist
    
    
    def _window_next(self):
        logger.info('getting a track from the window')
        while len(self.window) < self.max_window + 1:
            if len(self.pool) > 0:
                track = random.sample(self.pool, 1)[0]
                self.pool.remove(track)
                self.window.append(track)
            
            else:
                logger.warn('no track found in the pool, playlist might end up looping')
                break
        
        #logger.debug('window: %s', repr(self.window))
        track = self.window.pop(0)
        logger.debug('chosen track: %s', track)
        self.pool.add(track)
        
        # not needed since the window auto adjusts itself with every playing track
        # this only guarantees a tiny extra randomness when deleting tracks from the db
        """
        if len(self.window) > self.max_window:
            # remove extra tracks at the end of the window and place them in the pool
            logger.info('removing extra tracks from the window')
            self.pool.update(self.window[self.max_window:])
            self.window = self.window[:self.max_window]
        """
        
        return track
    
    def _enqueue(self, current):
        if current > self.buffer:
            # remove any extra tracks at the beginning of the playlist
            logger.info('removing %d extra tracks from the beginning of the playlist', current - self.buffer)
            self.mpd.delete((0, current - self.buffer))
            self.playlist = self.playlist[current - self.buffer:]
            current -= (current - self.buffer)
        
        logger.debug('playlist: %s', repr(self.playlist))
        
        while len(self.playlist) - current - 1 < self.buffer:
            # get a track from the window, add it to the playlist
            logger.info('enqueueing another track')
            track = self._window_next()
            self.mpd.add(track)
            self.playlist.append(track)
    
    def _update(self):
        # store old list of tracks
        old = self.tracks
        # get new list of tracks
        self.tracks = self._tracks()
        current = self.tracks
        
        self.total_songs = len(self.tracks)
        self.max_window = int(self.total_songs * self.window_size)
        logger.info('updated window size to %d', self.max_window)
        
        added = current - old
        removed = old - current
        
        # remove removed tracks from window/pool
        if removed:
            logger.debug('database removed tracks: %s', repr(removed))
            self.window = [t for t in self.window if t not in removed]
            self.pool = self.pool - removed
        
        # add new tracks to pool
        if added:
            logger.debug('database added tracks: %s', repr(added))
            self.pool.update(added)
    
    def shuffle(self):
        self.window = []
        self.tracks = self._tracks()
        self.pool = set(self.tracks)
        self.playlist = self._playlist()
        
        self.total_songs = len(self.tracks)
        self.max_window = int(self.total_songs * self.window_size)
        
        status = self.mpd.status()
        self._enqueue(int(status['song']))
        
        logger.info('starting shuffle with a %d window size and a buffer of %d songs on either side of the playlist',
                    self.max_window, self.buffer)
        
        while True:
            subsystem = list(self.mpd.idle())
            status = self.mpd.status()
            
            if 'database' in subsystem:
                logger.info('database updated')
                self._update()
            
            
            if 'player' in subsystem:
                logger.info('player state changed')
                self._enqueue(int(status['song']))
                
            elif 'playlist' in subsystem:
                logger.info('playlist updated')
                # store old playlist
                old = set(self.playlist)
                
                # get new playlist
                self.playlist = self._playlist()
                current = set(self.playlist)
                
                # compare and check for differences
                #matches = old & current
                added = current - old
                removed = old - current
                
                # remove new tracks from the window
                if added:
                    logger.debug('playlist added tracks: %s', repr(added))
                    self.window = [t for t in self.window if t not in added]
                    self.pool.update(added)
                
                # replace removed tracks if applicable
                if removed:
                    logger.debug('playlist removed tracks: %s', repr(removed))
                self._enqueue(int(status['song']))
#


def main():
    mpd = MPDClient()
    mpd.connect(host=config.MPD_HOST, port=config.MPD_PORT)
    mpd.iterate = True
    pw = config.get('MPD_PASSWORD', None)
    if pw is not None:
        mpd.password(pw)
    
    shuf = mpdshuffle(mpd, config.PLAYLIST_BUFFER, config.PLAYLIST_WINDOW)
    shuf.shuffle()
#


if __name__ == '__main__':
    try:
        main()
    except:
        logger.exception('exiting')

