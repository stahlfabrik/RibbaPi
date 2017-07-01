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

import time
import numpy as np
import random

import colorsys

from animation.abstract_animation import AbstractAnimation


class MoodlightAnimation(AbstractAnimation):
    def __init__(self, width, height, frame_queue, repeat=False,
                 mode="wish_down_up"):
        super().__init__(width, height, frame_queue, repeat)
        self.mode = mode
        self.colors = [(255, 0, 0), (255, 255, 0), (0, 255, 255), (0, 0, 255)]  # if empty choose random colors
        self.random = False  # how to step through colors
        self.hold = 10  # seconds to hold colors
        self.transition_duration = 10  # seconds to change from one to other
        self.frequency = 60  # frames per second
        print("MoodlightAnimation created")

    def ribbapi_hsv_to_rgb(self, h, s, v):
        # h is in degrees
        # s, v in percent
        h %= 360
        h /= 360
        s /= 100
        v /= 100
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return (int(r * 255), int(g * 255), int(b * 255))

    def ribbapi_rgb_to_hsv(self, r, g, b):
        r /= 255
        g /= 255
        b /= 255
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        return (h * 360, s * 100, v * 100)

    def color_wheel_generator(self, steps):
        # steps: how many steps to take to go from 0 to 360.
        increase = (360 - 0) / steps
        while True:
            for i in np.arange(0, 360, increase):
                color = self.ribbapi_hsv_to_rgb(i, 100, 100)
                yield color

    def cycle_selected_colors_generator(self, steps, hold):
        # steps: how many steps from one color to other color
        # hold: how many iterations to stay at one color
        current_color = None
        while True:
            for color in self.colors:
                if not current_color:
                    current_color = color
                    yield color
                else:
                    # rgb color
                    r, g, b = color
                    current_r, current_g, current_b = current_color
                    increase_r = (r - current_r) / steps
                    increase_g = (g - current_g) / steps
                    increase_b = (b - current_b) / steps
                    for _ in range(steps):
                        current_r += increase_r
                        current_g += increase_g
                        current_b += increase_b
                        current_color = (current_r, current_g, current_b)
                        color = (int(current_r), int(current_g), int(current_b))
                        yield color
                for _ in range(hold):
                    yield color

    def frame_generator(self, color_mode, style):
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        if color_mode == "colorwheel":
            colors = self.color_wheel_generator(500)
        elif color_mode == "cyclecolors":
            colors = self.cycle_selected_colors_generator(5, 100)

        while True:
            if style == "fill":
                frame[:, :] = next(colors)
                yield frame
            elif style == "random_dot":
                y = np.random.randint(0, self.height)
                x = np.random.randint(0, self.width)
                frame[y, x] = next(colors)
                yield frame
            elif style == "wish_down_up":
                color = next(colors)
                frame = np.concatenate((frame[1:16, :],
                                        np.array(color * self.width).reshape(1, self.width, 3)), axis=0)
                yield frame

    def animate(self):
        while self._running:
            if self.mode == "colorwheel":
                generator = self.frame_generator("colorwheel", "fill")

            elif self.mode == "cyclecolors":
                generator = self.frame_generator("cyclecolors", "random_dot")

            elif self.mode == "wish_down_up":
                generator = self.frame_generator("colorwheel", "wish_down_up")

            for frame in generator:
                if self._running:
                    self.frame_queue.put(frame.copy())
                else:
                    break
                time.sleep(1/self.frequency)
            # if self.repeat > 0:
            #     self.repeat -= 1
            # elif self.repeat == 0:
            #     self._running = False

    @property
    def kwargs(self):
        return {"width": self.width, "height": self.height,
                "frame_queue": self.frame_queue, "repeat": self.repeat}
