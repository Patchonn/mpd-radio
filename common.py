# -*- coding: utf-8 -*-
import random
import logging
import importlib.util
import os
import os.path

import clients.mpd

def get_config(env):
    config_path = os.environ.get(env)
    if config_path is not None:
        return Module(config_path)
    else:
        return Module()
#

def get_logger(name, level=logging.WARNING, filename=None):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s -- %(message)s', '%Y-%m-%d %H:%M:%S')
    
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    
    logger.addHandler(console)
    
    if filename is not None:
        file = logging.FileHandler(filename)
        file.setLevel(level)
        file.setFormatter(formatter)
        
        logger.addHandler(file)
    
    return logger
#

class Module(object):
    def __init__(self, filename=None):
        if filename is not None:
            module_name = os.path.splitext(os.path.basename(filename))[0]
            spec = importlib.util.spec_from_file_location(module_name, filename)
            self.__module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.__module)
            
        else:
            self.__module = object()
    
    def __getattr__(self, name):
        return getattr(self.__module, name)
    
    def get(self, name, default=None):
        return getattr(self.__module, name, default)
#

def id_generator(size=20, chars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
    return ''.join(random.choice(chars) for _ in range(size))
#


class TimeDiff(object):
    SECS = [86400, 3600, 60, 1]
    NAMES = ['days', 'hours', 'minutes', 'seconds']
    
    def __init__(self, tf, ts):
        self.diff = tf - ts
        
        rem = self.diff
        self._diffs = []
        for name, secs in zip(self.NAMES, self.SECS):
            times = rem // secs
            rem = rem % secs
            
            if times > 0:
                name = name if times != 1 else name[:-1]
                self._diffs.append('{} {}'.format(times, name))
                
        self._readable = ' '.join(self._diffs)
    
    def __str__(self):
        return self._readable
#



