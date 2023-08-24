import time
import math
import re
from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN as DISPLAY

from machine import I2C, Pin, RTC, Timer
import notecard 
from notecard import card, hub 

import images

# Check whether the RTC time has changed and if so redraw the display
def redraw_display_if_reqd():
    global year, month, day, wd, hour, minute, second, last_second
 
    year, month, day, wd, hour, minute, second, _ = rtc.datetime()
    if second != last_second:
        
        graphics.set_pen(BLACK)
        graphics.rectangle(0,0,32,7)
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

def update_weather(lFunc = None):
    res = webRequest('weather','?latitude=51.48&longitude=0.07&current_weather=true', lFunc)
    return res

def draw_weather(code,temp,unit):
    images.drawImage(graphics, (width-11), 0, weathercodes_to_image[code])
    

weathercodes_to_image={
    0:  images.SUN,
    1:  images.OVERCAST,
    2:  images.OVERCAST,
    3:  images.OVERCAST,
    45: images.FOG,
    46: images.FOG,
    51: images.RAIN,
    53: images.RAIN,
    55: images.RAIN,
    56: images.RAIN,
    57: images.RAIN,
    61: images.RAIN,
    63: images.RAIN,
    65: images.RAIN,
    66: images.RAIN,
    67: images.RAIN,
    71: images.SNOW,
    73: images.SNOW,
    75: images.SNOW,
    77: images.SNOW,
    80: images.RAIN,
    81: images.RAIN,
    82: images.RAIN,
    85: images.SNOW,
    86: images.SNOW,
    71: images.LIGHTNING,
    73: images.LIGHTNING,
    73: images.LIGHTNING,
}

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
epochtime += 14
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
    if (second == 0 and (minute % 5) == 0):
        weather = update_weather()
        current_weather=weather['body']['current_weather']
        draw_weather(current_weather['weathercode'],math.floor(current_weather['temperature']),'c')
    # update the display
    gu.update(graphics)
 
    time.sleep(0.01)

