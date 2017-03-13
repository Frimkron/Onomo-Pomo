#!/usr/bin/env python3

import os.path
import sys
import time
import simpleaudio
import argparse
import notify2
import configparser
from collections import namedtuple, OrderedDict

""" 
TODO: starting pomo count parameter
TODO: tray icon
TODO: different start and end sounds
TODO: toaster popups for windows & mac
TODO: pomo/break countdown
TODO: store pomo count
TODO: break end warning notification
TODO: break end warning sound
TODO: confirm state change option
TODO: pause on state change option
TODO: speaker beep sound option
TODO: run custom command on state start/end
"""

VERSION_NUMBER = 1,2,0
MESSAGE_BY_CONSOLE = 'console'
MESSAGE_BY_DESKTOP = 'desktop'
MESSAGE_BYS = MESSAGE_BY_CONSOLE, MESSAGE_BY_DESKTOP
DEFAULT_CONFIG_FILE = os.path.join(os.path.expanduser('~'),'.config','onomo.conf')
CONFIG_SECTION_MAIN = 'main'
OWN_DIR = os.path.abspath(os.path.dirname(__file__))

ConfigVar = namedtuple('ConfigVar','longname shortname validator default suggested description')


class NameSet(tuple):
    def __str__(self):
        return ','.join(map(str,self))


def posnonz(func):
    def wrapper(val):
        v = func(val)
        if v <= 0:
            raise ValueError()
        return v
    wrapper.__name__ = func.__name__
    return wrapper


def nameset(values):
    def validator(val):
        parts = [str.strip(p) for p in val.split(',')]
        if not all([p in values for p in parts]):
            raise ValueError()
        return NameSet(parts)
    validator.__name__ = 'nameset'
    return validator
    

CONFIG_VARS = [ConfigVar(*args) for args in [
    ('pomomins',  'p', posnonz(float),       25,   None,
                'Length of Pomodoros in minutes.'),
    ('shortmins', 's', posnonz(float),       5,    None,
                'Length of short breaks in minutes.'),
    ('longmins',  'l', posnonz(float),       30,   None,
                'Length of long breaks in minutes.'),
    ('alertsound','a', str,                  os.path.join(OWN_DIR,'brring.wav'),None,
                'Audio file to play at the end of a pomodoro or break.'),
    ('pomosound',None, str,                  '', os.path.join(OWN_DIR,'ticktock.wav'),
                'Audio file to loop during a Pomodoro.'),
    ('breaksound',None,str,                  '', os.path.join(OWN_DIR,'ticktock.wav'),
                'Audio file to loop during a break.'),
    ('longper',   'n', posnonz(int),         4,    None,
                'Number of pomodoros between long breaks.'),
    ('messageby', 'm', nameset(MESSAGE_BYS), NameSet((MESSAGE_BY_CONSOLE,MESSAGE_BY_DESKTOP)), None,
                'How to display message at the start of a pomodoro or break.'),
]]

    
def product(v):
    n = v.pop(0)
    while len(v) > 0:
        n *= v.pop(0)
    return n
    
    
def dur_format(seconds):
    s = ""
    seconds = int(seconds)
    units = [(60,'hr'),(60,'m'),(1,'s')]
    while len(units) > 0:
        n = product([x[0] for x in units])
        rep = units.pop(0)[1]
        v,seconds = divmod(seconds,n)
        if v > 0 or (len(units) == 0 and len(s) == 0):
            s += '{}{} '.format(v,rep)
    return s.strip()
    
    
def make_notifier(message_bys):
    notis = []
    if MESSAGE_BY_DESKTOP in message_bys:
        notify2.init("Onomo-Pomo")
        notis.append(lambda m: notify2.Notification(m).show())
    if MESSAGE_BY_CONSOLE in message_bys:
        notis.append(lambda m: print(m))
    return lambda m: [n(m) for n in notis]
            
            
def make_sounder(filepath):
    if not filepath:
        return lambda: None
    sound = simpleaudio.WaveObject.from_wave_file(filepath)
    def sounder():
        play = sound.play()
        play.wait_done()
    return sounder
    
    
def make_timer(mins,soundpath):
    if soundpath:
        sound = simpleaudio.WaveObject.from_wave_file(soundpath)
        def timer():
            starttime = time.time()
            while time.time()-starttime < mins*60:
                play = sound.play()
                play.wait_done()
        return timer
    else:
        return lambda: time.sleep(mins*60)
    

def sound_file_error_quit(e):
    sys.exit("Error loading audio file: {}".format(str(e)))
    

ap = argparse.ArgumentParser(description=u"Onomo-Pomo: a simple timer for the Pomodoro working technique")
for configvar in CONFIG_VARS:
    argargs = ['--{}'.format(configvar.longname)]
    argkwargs = {
        'type': configvar.validator, 
        'help': '{} Defaults to "{}"'.format(configvar.description,configvar.default), 
    }
    if configvar.shortname:
        argargs.insert(0, '-{}'.format(configvar.shortname))
    ap.add_argument(*argargs, **argkwargs)
    
ap.add_argument('-c','--configfile', default=DEFAULT_CONFIG_FILE,
                help="Config file to use. Defaults to {}".format(DEFAULT_CONFIG_FILE))
ap.add_argument('-v','--version',action="store_true", help="Show version number and exit")
args = ap.parse_args()

if args.version:
    print("Onomo-Pomo v{}".format('.'.join(map(str,VERSION_NUMBER))))
    sys.exit()

args.configfile = os.path.expanduser(args.configfile)
if not os.path.exists(args.configfile):
    os.makedirs(os.path.dirname(args.configfile), exist_ok=True)
    fileconf = configparser.ConfigParser(allow_no_value=True)
    fileconf[CONFIG_SECTION_MAIN] = OrderedDict()
    for configvar in CONFIG_VARS:
        suggested = configvar.suggested if configvar.suggested is not None else configvar.default
        fileconf[CONFIG_SECTION_MAIN]['\x23\x23 {}'.format(configvar.description)] = None
        fileconf[CONFIG_SECTION_MAIN]['\x23 {} = {}\n'.format(configvar.longname, suggested)] = None
    with open(args.configfile,'w') as f:
        fileconf.write(f)

fileconf = configparser.ConfigParser()
fileconf.read(args.configfile)

conf = {}
for configvar in CONFIG_VARS:
    value = configvar.default
    filevalue = fileconf[CONFIG_SECTION_MAIN].get(configvar.longname,None)
    if filevalue is not None:
        try:
            value = configvar.validator(filevalue)
        except ValueError:
            sys.exit("Invalid value \"{}\" for option \"{}\" in config file \"{}\"".format(
                     filevalue,configvar.longname,args.configfile))
    argvalue = getattr(args,configvar.longname)
    if argvalue is not None:
        value = argvalue
    conf[configvar.longname] = value

try:
    sounder = make_sounder(conf['alertsound'])
except IOError as e:
    sound_file_error_quit(e)

notifier = make_notifier(conf['messageby'])

try:
    pomo_timer = make_timer(conf['pomomins'],conf['pomosound'])
except IOError as e:
    sound_file_error_quit(e)

try:
    short_timer = make_timer(conf['shortmins'],conf['breaksound'])
except IOError as e:
    sound_file_error_quit(e)

try:
    long_timer = make_timer(conf['longmins'],conf['breaksound'])
except IOError as e:
    sound_file_error_quit(e)

checks = 0

while True:

    # Pomodoro
    notifier("Pomodoro ({} - {} more until long break)".format(
            dur_format(conf['pomomins']*60), conf['longper']-(checks+1)))            
    pomo_timer()        
    sounder()
    checks += 1
    
    # Break
    if checks >= conf['longper']:    
        notifier("Long break ({})".format(dur_format(conf['longmins']*60)))
        long_timer()
        checks = 0
        
    else:    
        notifier("Short break ({})".format(dur_format(conf['shortmins']*60)))
        short_timer()
        
    sounder()
