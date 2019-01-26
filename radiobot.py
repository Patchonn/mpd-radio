#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import time
import traceback
import urllib.parse

import common
import clients.mpd
from clients.mpd import MpdConnection
from clients.irc import IrcConnection, Nick

config = common.get_config('MPD_RADIO_CONFIG')
logger = common.get_logger('bot', level=config.LOG_LEVEL)

class SongInfo(clients.mpd.SongInfo):
    def __init__(self, song, elapsed=None):
        super(SongInfo, self).__init__(song, elapsed)
        
        host = config.get('MUSIC_HOST', None)
        if host is not None:
            self.url = '{}/{}'.format(host, urllib.parse.quote(self.filename))
#

class Vote(object):
    def __init__(self, song, nick=None, required=5):
        self.song = song
        self.starter = nick
        self.required = required
        self.voted = set()
        self.banned = set()
        
        if nick is not None:
            self.voted.add(nick)
    
    def vote(self, nick):
        if nick not in self.banned:
            self.voted.add(nick)
    
    def votes(self):
        return len(self.voted)
    
    def done(self):
        return len(self.voted) >= self.required
    
    def ban(self, nick):
        self.voted.add(nick)
    
    def __str__(self):
        return '{}/{}'.format(len(self.voted), self.required)
#

class IrcBot(object):
    def __init__(self, irc, mpd, extra):
        self._irc = irc
        self._nick = self._irc._nick
        self._admin = None
        self._mpd = mpd
        self._extra = extra
        self._gen_auth()
        self._init()
    
    def _gen_auth(self):
        self._auth_code = common.id_generator()
        with open('auth.txt', 'w+') as f:
            f.write(self._auth_code)
    
    def _loop(self):
        for msg in self._irc:
            #logger.debug(msg)
            
            nick = Nick(msg['nick'])
            if msg['command'] == 'PRIVMSG':
                target = msg['params'][0]
                message = msg['params'][1]
                
                if target[0] != '#':
                    target = msg['nick']
                
                # minecraft bots support
                match = re.match(r'^<([^>]+)> (.*)$', message)
                if match is not None:
                    nick = Nick(match.group(1), msg['nick'])
                    message = match.group(2)
                
                if message.startswith(config.IRCBOT_CMD):
                    args = message.split(' ')
                    
                    cmd = args[0][1:]
                    args = args[1:]
                    
                    if cmd[0] != '_':
                        func = getattr(self, cmd, None)
                        reply = self._extra.get(cmd, None)
                        if func is not None:
                            try:
                                func(nick, target, *args)
                            except Exception as e:
                                # ignore non existent and wrong arguments
                                #self._irc.privmsg(target, 'error: {}'.format(e))
                                traceback.print_exc()
                                pass
                            
                        elif reply is not None:
                            self._irc.privmsg(target, reply)
                            
                
            elif msg['command'] == '474':
                # 474 => ban error
                #{'nick': 'irc.neet.link', 'user': None, 'host': None, 'command': '474', 'params': ['radiobot', '#botdev', 'Cannot join channel (+b)']}
                logger.error('I\'ve been banned, exiting')
                break
                
            elif msg['command'] == 'JOIN':
                target = msg['params'][0]
                self._on_join(nick, target)
                
            elif msg['command'] == 'NICK':
                new_nick = msg['params'][0]
                self._on_join(nick, new_nick)
                
            elif (msg['command'] == 'PART' or msg['command'] == 'QUIT'):
                target = msg['params'][0]
                self._on_quit(nick, target)
                
            elif msg['command'] == 'KICK':
                ['#botdev', 'radiobot', 'myon']
                target = msg['params'][0]
                kicked = msg['params'][1]
                kicked_by = msg['params'][2]
                self._on_kick(nick, target, kicked, kicked_by)
    
    def auth(self, nick, target, code):
        if code == self._auth_code:
            self._auth_code = None
            self._admin = nick
            self._irc.privmsg(target, '{}~'.format(nick))
    
    def deauth(self, nick, target=None):
        if nick == self._admin:
            self._admin = None
            self._gen_auth()
    
    
    def _init(self):
        self._search_idx = []
        self._search_file = {}
        
        self._request_timeout = {}
        self._skip_vote = None
    
    # commands
    
    def _on_join(self, nick, target):
        self._request_timeout[nick] = int(time.time())
    
    def _on_nick_change(self, nick, new_nick):
        self._request_timeout[new_nick] = self._request_timeout.get(nick, None)
    
    def _on_quit(self, nick, target):
        if self._admin is not None and nick == self._admin:
            self.deauth(self._admin)
    
    def _on_kick(self, nick, target, kicked, kicked_by):
        # auto re-join
        if kicked == self._nick:
            self._irc.join(target)
    
    def playing(self, nick, target):
        status = self._mpd.status()
        current = self._mpd.currentsong()
        
        info = SongInfo(current, status['elapsed'])
        
        self._irc.privmsg(target, 'now playing: {}'.format(info))
    
    def download(self, nick, target):
        current = self._mpd.currentsong()
        
        info = SongInfo(current)
        
        # TODO this url should come from somewhere else
        host = config.get('MUSIC_HOST', None)
        if host is not None:
            url = '{}/{}'.format(host, urllib.parse.quote(info.filename))
            self._irc.privmsg(target, info.url)
    
    def filename(self, nick, target):
        current = self._mpd.currentsong()

        info = SongInfo(current)

        if host is not None:
            self._irc.privmsg(target, info.filename)
    
    def search(self, nick, target, *args):
        tag = ' '.join(args)
        
        self._search_idx = []
        self._search_file = {}
        result = list(self._mpd.search('any', tag))
        
        if len(result) < config.IRCBOT_SEARCH_LIMIT:
            result.extend(self._mpd.search('file', tag))
        
        # filter duplicates
        used = set()
        result = [x for x in result if x['file'] not in used and (used.add(x['file']) or True)]
        
        if len(result) > 0:
            i = 0
            for t in result:
                if i >= config.IRCBOT_SEARCH_LIMIT: break
                
                info = SongInfo(t)
                
                self._search_idx.append(info)
                self._search_file[info.filename] = info
                
                self._irc.privmsg(target, '{}: {}'.format(i, info))
                
                i += 1
            
        else:
            self._irc.privmsg(target, 'nothing found')
    
    def _add(self, file):
        status = self._mpd.status()
        songid = self._mpd.addid(file)
        self._mpd.moveid(songid, int(status['song']) + 1)
    
    def request(self, nick, target, *args):
        id = args[0] if len(args) == 1 else ' '.join(args)
        
        try: info = self._search_idx[int(id)]
        except: info = self._search_file.get(id, None)
        
        if info is not None:
            last_request = self._request_timeout.get(nick, None)
            next_request = last_request + config.IRCBOT_REQUEST_TIMEOUT if last_request is not None else None
            now = int(time.time())
            
            if last_request is None or now > next_request or nick == self._admin:
                self._add(info.file)
                self._irc.privmsg(target, 'song was added to the queue: {}'.format(info))
                self._request_timeout[nick] = now
                
            else:
                self._irc.privmsg(target, 'you can only request another song after {}'.format(common.TimeDiff(next_request, now)))
    
    def _skip(self):
        self._mpd.next()
    
    def skip(self, nick, target):
        if nick == self._admin:
            self._skip()
            self._skip_vote = None
            self._irc.privmsg(target, 'skipped')
            
        else:
            current = self._mpd.currentsong()
            info = SongInfo(current)
            
            if self._skip_vote is None or self._skip_vote.song != info:
                self._skip_vote = Vote(info, nick, config.IRCBOT_SKIP_VOTES)
                self._irc.privmsg(target, 'skip vote started for: {}'.format(info))
            
            else:
                self._skip_vote.vote(nick)
                
            if self._skip_vote.done():
                self._skip()
                self._skip_vote = None
                self._irc.privmsg(target, 'skipped')
                
            else:
                self._irc.privmsg(target, 'skip vote: {}'.format(self._skip_vote))
    
#

def main():
    extra_commands = {
        'stream': config.get('STREAM_LINK', None),
        'radio': config.get('RADIO_LINK', None),
        'm3u8': config.get('PLAYLIST_LINK', None)
    }
    
    irc = IrcConnection(config.IRC_HOST, config.IRC_PORT, config.IRC_NICK, password=config.IRC_PASS, ssl=True)
    irc.join(config.IRC_CHANNEL)
    mpd = MpdConnection(config.MPD_HOST, config.MPD_PORT, config.MPD_PASSWORD, iterate=True)
    bot = IrcBot(irc, mpd, extra=extra_commands)
    bot._loop()
#

if __name__ == '__main__':
    main()

