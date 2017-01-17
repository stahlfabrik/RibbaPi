#!/usr/bin/env python3

# RibbaPi - APA102 LED matrix controlled by Raspberry Pi in python
# Copyright (C) 2016  Christoph Stahl
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import math
import time
import numpy as np
from PIL import Image, ImageDraw

from animation.abstract_animation import AbstractAnimation

LEN_HOUR = 2


class ClockAnimation(AbstractAnimation):
    def __init__(self, width, height, frame_queue, repeat=False,
                 mode='current', background_color=(50, 70, 230)):
        super().__init__(width, height, frame_queue, repeat)
        self.name = "clock"
        self.mode = mode
        self.background_color = background_color
        watch = Image.open("resources/clock/watch_16x16_without_arms.png")
        self.background = Image.new("RGB", watch.size, background_color)
        self.background.paste(watch, mask=watch.split()[3])

    def minute_point(self, middle, minute):
        minute %= 60
        angle = 2*math.pi * minute/60 - math.pi/2
        length = 2
        while True:
            x = int(middle[0] + length * math.cos(angle))
            y = int(middle[1] + length * math.sin(angle))
            if x == 5 or x == 10:
                break
            if y == 5 or y == 10:
                break
            length += 1
        return (x, y)

    def hour_point(self, middle, hour):
        hour %= 12
        angle = 2*math.pi * hour/12 - math.pi/2
        x = int(middle[0] + LEN_HOUR * math.cos(angle))
        y = int(middle[1] + LEN_HOUR * math.sin(angle))
        if x > 9:
            x = 9
        if y > 9:
            y = 9
        return (x, y)

    def middle_point(self, minute):
        return (8, 8)
#        if minute > 0 and minute <=15:
#            return (7,8)
#        elif minute > 15 and minute <=30:
#            return (7,7)
#        elif minute > 30 and minute <=45:
#            return (8,7)
#        else:
#            return (8,8)

    def add_hour_minute_hands(self, image, hour, minute):
        middle = self.middle_point(minute)
        draw = ImageDraw.Draw(image)
        draw.line([self.middle_point(minute),
                   self.minute_point(middle, minute)], fill=(0, 0, 0))
        draw.line([self.middle_point(minute),
                   self.hour_point(middle, hour)], fill=(0, 0, 0))

    def animate(self):
        while self._running:
            if self.mode == 'current':
                local_time = time.localtime()
                image = self.background.copy()
                self.add_hour_minute_hands(image,
                                           local_time.tm_hour,
                                           local_time.tm_min)
                self.frame_queue.put(np.array(image).copy())
                time.sleep(1)
            else:
                hour = 0
                for i in range(12*60):
                    if not self._running:
                        break
                    if i % 60 == 0:
                        hour += 1
                        hour %= 12
                    minute = i % 60
                    image = self.background.copy()
                    self.add_hour_minute_hands(image, hour, minute)
                    self.frame_queue.put(np.array(image).copy())
                    time.sleep(0.1)

    @property
    def kwargs(self):
        return {"width": self.width, "height": self.height,
                "frame_queue": self.frame_queue, "repeat": self.repeat,
                "mode": self.mode, "background_color": self.background_color}


    def dump_animation(self, min_step=5):
        hour = 0
        for i in range(1, 12*60+1):
            if i % 60 == 0:
                hour += 1
                hour %= 12
            minute = i % 60
            if minute % min_step == 0:
                cp = self.background.copy()
                draw = ImageDraw.Draw(cp)
                draw.line([self.middle_point(minute),
                           self.minute_point(minute)], fill=(0, 0, 0))
                draw.line([self.middle_point(minute),
                           self.hour_point(hour)], fill=(0, 0, 0))
                cp.save("{}.bmp".format(i))
