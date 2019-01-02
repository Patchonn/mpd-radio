# -*- coding: utf-8 -*-
import muirc

class IrcConnection(muirc.Connection):
    def __init__(self, host, port, nick, ssl=False):
        self._nick = nick
        super(IrcConnection, self).__init__((host, port), use_ssl=ssl)
        self.nick(nick)
        self.user(nick, '0', '*', nick)
        
        for msg in self:
            # TODO save motd?
            
            # 376 => MOTD end of motd
            # 422 => MOTD is missing
            if msg['command'] == '376' or msg['command'] == '422':
                break
    
    def iter(self, timeout = None):
        it = super(IrcConnection, self).iter(timeout)
        for msg in it:
            if msg['command'] == 'PING':
                self.pong(*(msg['params']))
            else:
                yield msg
#

class Nick(object):
    def __init__(self, nick, proxy=None):
        self.proxy = proxy
        self.nick = nick
    
    def __eq__(self, other):
        return isinstance(other, Nick) and self.proxy == other.proxy and self.nick == other.nick
    
    def __str__(self):
        return self.nick
    
    def __hash__(self):
        return hash(self.nick)
#

