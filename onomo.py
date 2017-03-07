#!/usr/bin/env python3

import os.path
import sys
import time
import simpleaudio
import argparse
import notify2

""" 
TODO: starting pomo count parameter
TODO: config file
TODO: tray icon
TODO: different start and end sounds
TODO: configurable pause between breaks/pomos
TODO: ticking sound
TODO: toaster popups for windows & mac
TODO: pomo/break countdown
TODO: store pomo count
"""

VERSION_NUMBER = 1,0,1
DEFAULT_POMO_MINS = 25
DEFAULT_SHORT_MINS = 5
DEFAULT_LONG_MINS = 30
DEFAULT_AUDIO_FILE = os.path.join(os.path.dirname(__file__),'brring.wav')
DEFAULT_LONG_PER = 4
MESSAGE_BY_CONSOLE = 'console'
MESSAGE_BY_DESKTOP = 'desktop'
MESSAGE_BYS = MESSAGE_BY_CONSOLE, MESSAGE_BY_DESKTOP
DEFAULT_MESSAGE_BYS = MESSAGE_BY_CONSOLE, MESSAGE_BY_DESKTOP


def posnonz(func):
    def wrapper(val):
        v = func(val)
        if v <= 0:
            raise ValueError()
        return v
    wrapper.__name__ = func.__name__
    return wrapper
    
    
def messagebys(value):
    vals = list(map(str.strip,value.split(',')))
    for v in vals:
        if v not in MESSAGE_BYS:
            raise ValueError()
    return vals
    
    
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
    return lambda: sound.play()
    

ap = argparse.ArgumentParser(description=u"Onomo-Pomo: a simple timer for the Pomodoro working technique")
ap.add_argument('-p','--pomomins',type=posnonz(float),default=DEFAULT_POMO_MINS,
                help="Length of pomodoros in minutes. Defaults to {}".format(DEFAULT_POMO_MINS))
ap.add_argument('-s','--shortmins',type=posnonz(float),default=DEFAULT_SHORT_MINS,
                help="Length of short breaks in minutes. Defaults to {}".format(DEFAULT_SHORT_MINS))
ap.add_argument('-l','--longmins',type=posnonz(float),default=DEFAULT_LONG_MINS,
                help="Length of long breaks in minutes. Defaults to {}".format(DEFAULT_LONG_MINS))
ap.add_argument('-a','--audiofile',default=DEFAULT_AUDIO_FILE,nargs='?',
                help="Audio file to play at the end of a pomodoro or break. "
                     "Defaults to \"{}\". Use \"\" for no audio".format(DEFAULT_AUDIO_FILE))
ap.add_argument('-n','--longper',type=posnonz(int),default=DEFAULT_LONG_PER,
                help="Number of pomodoros between long breaks. Defaults to {}".format(DEFAULT_LONG_PER))
ap.add_argument('-m','--messageby',type=messagebys,default=DEFAULT_MESSAGE_BYS,
                help="How to display message at the start of a pomodoro or break. "
                     "Comma-separated values from: {}. Defaults to \"{}\".".format(','.join(MESSAGE_BYS),
                     ','.join(DEFAULT_MESSAGE_BYS)))
ap.add_argument('-v','--version',action="store_true",
                help="Show version number and exit")
args = ap.parse_args()

if args.version:
    print("Onomo-Pomo v{}".format('.'.join(map(str,VERSION_NUMBER))))
    sys.exit()

try:
    sounder = make_sounder(args.audiofile)
except IOError as e:
    sys.exit("Error loading audio file \"{}\": {}".format(args.audiofile,str(e)))

notifier = make_notifier(args.messageby)

checks = 0

while True:
    notifier("Pomodoro ({} - {} more until long break)".format(dur_format(args.pomomins*60),args.longper-(checks+1)))
    time.sleep(args.pomomins*60)
    sounder()
    checks += 1
    if checks >= args.longper:
        notifier("Long break ({})".format(dur_format(args.longmins*60)))
        time.sleep(args.longmins*60)
        checks = 0
    else:
        notifier("Short break ({})".format(dur_format(args.shortmins*60)))
        time.sleep(args.shortmins*60)
    sounder()
