import time
import math
import re
from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN as DISPLAY

from machine import I2C, Pin, RTC, Timer
import notecard 
from notecard import card, hub 

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

celltime = card.time(nCard)
epochtime = celltime["time"]

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
 
while True:
    redraw_display_if_reqd()
 
    # update the display
    gu.update(graphics)
 
    time.sleep(0.01)