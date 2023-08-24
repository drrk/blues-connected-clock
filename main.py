import time
import math
import re
from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN as DISPLAY

from machine import I2C, Pin, RTC, Timer
import notecard 
from notecard import card, hub 

import images

def loading(x,y, text):
    state = 0
    w = graphics.measure_text(text, 1)
    graphics.set_pen(YELLOW)
    graphics.text(text, x, y, scale = 1)
    def inner():
        nonlocal state, w, x, y
        if state == 0:
            for i in range(5):
                graphics.set_pen(BLACK)
                graphics.rectangle(x + w + (i*3), y + 5, 2, 2)       
        for i in range(state):
            graphics.set_pen(YELLOW)
            graphics.rectangle(x + w + (i*3), y + 5,2,2)
        state += 1
        state = state % 5
    return inner


def split_number(num):
    if num > 99:
        raise ValueError()
    lsd = num % 10
    msd = (num - lsd) // 10
    return (msd, lsd)


def draw_clock_divider(x, y):
    # two points should be at y+1 and y+5
    # add space before divider
    graphics.pixel(x + 1, y + 1)
    graphics.pixel(x + 1, y + 3)


def draw_clock_pair(x, y, num):
    (msd,lsd) = split_number(num)
    graphics.text(str(msd), x ,y , scale = 1)   
    graphics.text(str(lsd), x + 4, y, scale = 1) # Font 3 width + 1 space    


def draw_clock(x, y, hour, minute, second):
    graphics.set_pen(BLACK)
    graphics.rectangle(x, y, 27, 5)  # 3 pairs of numbers, 2 dividers (7+7+7+3+3) 
    graphics.set_pen(YELLOW)
    graphics.set_font(font3x5)
    
    draw_clock_pair(x, y, hour)
    x += 7 # Pair of numbers is 2*4 plus 1 space
    draw_clock_divider(x, y)
    x += 3 # Divider is space points, then add a space
    
    draw_clock_pair(x, y, minute)
    x += 7
    draw_clock_divider(x, y)
    x += 3
    
    draw_clock_pair(x, y, second)

    
def update_clock(timer = None):
    global second, minute
    year, month, day, wd, hour, minute, second, _ = rtc.datetime()
    x = 0
    y = 0
    draw_clock(x, y, hour, minute, second)


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
    
    graphics.set_pen(BLUE)
    graphics.set_font(font3x5)
    tempstring = "{}{}".format(temp,unit)
    graphics.text(tempstring,0,6,0,1)

def update_gfx(timer = None):
    # update the display
    gu.update(graphics)

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

# create galactic object and graphics surface for drawing
gu = GalacticUnicorn()
graphics = PicoGraphics(DISPLAY)

width = GalacticUnicorn.WIDTH
height = GalacticUnicorn.HEIGHT

# set up some pens to use later
WHITE  = graphics.create_pen(255, 255, 255)
BLACK  = graphics.create_pen(0, 0, 0)
BLUE   = graphics.create_pen(0, 0, 255)
YELLOW = graphics.create_pen(255, 255, 0)
CYAN   = graphics.create_pen(0, 128, 128)

font3x5 = open("tiny.bitmapfont", "rb").read()

# set the font
graphics.set_font("bitmap8")
gu.set_brightness(0.6)
graphics.set_pen(BLACK)
graphics.clear()
update_loading = loading(0, 0, "Loading")

dstupdate = 0

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
  update_loading()
  gu.update(graphics)
  time.sleep(1)

tzInfo = get_tz_info(update_loading)
weather = update_weather(update_loading)

celltime = card.time(nCard)
epochtime = celltime["time"]
epochtime += tzInfo['offset']
if tzInfo['dstactive']:
    epochtime += tzInfo['dstoffset']
    dstupdate = tzInfo['dstchange']
    
graphics.set_pen(BLACK)
graphics.clear()
gu.update(graphics)

print(weather)
current_weather=weather['body']['current_weather']
draw_weather(current_weather['weathercode'],math.floor(current_weather['temperature']),'c')

tm = time.gmtime(epochtime)
rtc = machine.RTC()
rtc.datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], 0, 0))

year, month, day, wd, hour, minute, second, _ = rtc.datetime()
last_second = second

clock_timer = Timer(mode=Timer.PERIODIC, period=1000, callback=update_clock)
gfx_timer = Timer(mode=Timer.PERIODIC, period=100, callback=update_gfx)

while True:
    #if gu.is_pressed(GalacticUnicorn.SWITCH_BRIGHTNESS_UP):
    #    gu.adjust_brightness(+0.005)

    #if gu.is_pressed(GalacticUnicorn.SWITCH_BRIGHTNESS_DOWN):
    #    gu.adjust_brightness(-0.005)
 
    # Run once a second tasks
    if (last_second != second):
        last_second = second
        if (second == 0 and minute == 0):
            weather = update_weather()
            current_weather=weather['body']['current_weather']
            draw_weather(current_weather['weathercode'],math.floor(current_weather['temperature']),'c')
            
    time.sleep(0.01)
