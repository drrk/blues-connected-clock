import time
import math
import re
from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN as DISPLAY

from machine import I2C, Pin, RTC, Timer
import notecard 
from notecard import card, hub 

# Check whether the RTC time has changed and if so redraw the display
def redraw_display_if_reqd():
    global year, month, day, wd, hour, minute, second, last_second
 
    year, month, day, wd, hour, minute, second, _ = rtc.datetime()
    if second != last_second:
        
        graphics.set_pen(BLACK)
        graphics.clear()
        graphics.set_pen(WHITE)

        
        clock = "{:02}:{:02}:{:02}".format(hour, minute, second)       
        graphics.text(clock, 0, 0, scale=1)
        last_second = second

def webRequest(route,path,lFunc = None):
    nCard.Transaction({'req': 'hub.set', 'on': True})
    connected = False
    while connected == False:
        res = card.status(nCard)
        connected = res.get('connected',False)
        if lFunc != None:
            lFunc()
            gu.update(graphics)
        time.sleep(1)
    res = nCard.Transaction({'req': 'web.get', 'route': route, 'name': path})
    
    nCard.Transaction({'req': 'hub.set', 'off': True})
    return res

def iso8601toepoch(iso8601):
    # Simple implementation for convertion the ISO8601 dates in DTC start and end
    # If TZ is not Z, raise error
    match = re.match('^(\d\d\d\d)-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)Z$',iso8601)
    if match == None:
        raise ValueError('Invalid time value')
    stringValues = match.groups()
    intValues = tuple(map(int, stringValues))
    
    return time.mktime(intValues + (0,0))  

def get_tz_info(lFunc = None):
    celltime = card.time(nCard)
    tz = celltime['zone'].split(',')[1]
    path = '/TimeZone/zone?timeZone={zone}'.format(zone=tz)
    res = webRequest('time',path,lFunc)
    ret = {}
    if (res['body'].get('hasDayLightSaving', False)):
        dstInterval = res['body']['dstInterval']
        ret['dstoffset'] = dstInterval['dstOffsetToStandardTime']['seconds']
        dstActive = res['body']['isDayLightSavingActive']
        ret['dstactive'] = dstActive
        if dstActive:
            ret['dstchange'] = iso8601toepoch(dstInterval['dstEnd'])
        else:
            ret['dstchange'] = iso8601toepoch(dstInterval['dstStart'])
            
    ret['offset'] = res['body']['standardUtcOffset']['seconds']
    return ret



### MAIN

# Create I2C instance 
i2c=I2C(0, freq=400000)   

# Connect to Notecard   
nCard = notecard.OpenI2C(i2c, 0, 0) 

# Set ProductUID 
productUID = "com.blues.kjohnson:connectedclock"
hub.set(nCard, product=productUID, mode="periodic", outbound=15, inbound=60)

cardInit = False 
while cardInit == False:
  celltime = card.time(nCard)
  if "time" in celltime:
    # If we don't know location, we can't adjust for TZ
    if celltime.get('zone', 'UTC,Unknown') != 'UTC,Unknown':
        cardInit = True
  time.sleep(1)

tzInfo = get_tz_info()

celltime = card.time(nCard)
epochtime = celltime["time"]
epochtime += tzInfo['offset']
if tzInfo['dstactive']:
    epochtime += tzInfo['dstoffset']
    dstupdate = tzInfo['dstchange']
tm = time.gmtime(epochtime)
rtc = machine.RTC()
rtc.datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], 0, 0))

# create galactic object and graphics surface for drawing
gu = GalacticUnicorn()
graphics = PicoGraphics(DISPLAY)

width = GalacticUnicorn.WIDTH
height = GalacticUnicorn.HEIGHT

# set up some pens to use later
WHITE  = graphics.create_pen(255, 255, 255)
BLACK  = graphics.create_pen(0, 0, 0)


# set the font
graphics.set_font("bitmap8")
gu.set_brightness(0.4)
graphics.set_pen(BLACK)
graphics.clear()

year, month, day, wd, hour, minute, second, _ = rtc.datetime()
last_second = second
 


while True:
    redraw_display_if_reqd()
 
    # update the display
    gu.update(graphics)
 
    time.sleep(0.01)
