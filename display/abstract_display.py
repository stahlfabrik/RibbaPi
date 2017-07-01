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

"""
This module is the abstract representation of a pixel matrix display.
"""

import abc
import numpy as np
import time


class AbstractDisplay(abc.ABC):
    def __init__(self, width=16, height=16):
        self.width = width
        self.height = height
        self.num_pixels = self.height * self.width
        self._buffer = np.zeros((self.height, self.width, 3),
                                dtype=np.uint8)  # 3 for red, green, blue
        self.brightness = 1.0

    @property
    def buffer(self):
        """The buffer contains the rgb data to be displayed."""
        return self._buffer

    @buffer.setter
    def buffer(self, value):
        if isinstance(value, np.ndarray):
            if self._buffer.shape == value.shape:
                #del self._buffer
                self._buffer = value

    def clear_buffer(self):
        #del self._buffer
        self._buffer = np.zeros_like(self._buffer)

    @abc.abstractmethod
    def show(self, gamma=False):
        """Display the contents of buffer on display. Gamma correction can be
        toggled."""

    def set_brightness(self, brightness):
        """Set the brightness (float) 0.0 to 1.0 value"""
        if brightness > 1.0:
            self.brightness = 1.0
        elif brightness < 0.0:
            self.brightness = 0.0
        else:
            self.brightness = brightness

    def set_pixel_at_index(self, index, color):
        """Set pixel at logical position index (from top left counted row-wise)
        to color, which must be a rgb values tuple"""
        if (index < 0) or (index >= self.num_pixels):
            return
        index *= 3
        self._buffer.put([index, index+1, index+2], color)

    def set_pixel_at_coord(self, x, y, color):
        """Set pixel at coordinate x,y to color, which must be a rgb values
        tuple"""
        if (x < 0) or (x >= self.width) or (y < 0) or (y >= self.height):
            return
        self._buffer[y, x] = color

    def set_buffer_with_flat_values(self, rgb_values):
        try:
            rgb_values = np.array(rgb_values, dtype=np.uint8)
            rgb_values.resize((self.num_pixels * 3,))
            rgb_values = rgb_values.reshape(self.height, self.width, 3)
        except:
            return
        #del self._buffer
        self._buffer = rgb_values

    def create_test_pattern(self):
        # written for 16x16 displays
        self.clear_buffer()
        values = np.arange(0, 256, int(256/(self.width-1)), dtype=np.uint8)
        #self._buffer[0:self.width/4*1, :, 0:3] = \
        #    self._buffer[0:4, :, 0:3] + \
        #    np.resize(values, (3, self.width)).transpose()
        self._buffer[0:self.width/4*1, :, 0:3] += \
            np.resize(values, (3, self.width)).transpose()
        self._buffer[self.width/4*1:self.width/4*2, :, 0] += values
        self._buffer[self.width/4*2:self.width/4*3, :, 1] += values
        self._buffer[self.width/4*3:self.width/4*4, :, 2] += values

    def run_benchmark(self, gamma=False):
        total = 0
        repeat = self.num_pixels * 10
        for i in range(repeat):
            start = time.time()
            self.set_pixel_at_index(i % self.num_pixels, (255, 255, 255))
            self.show(gamma)
            self.clear_buffer()
            end = time.time()
            diff = end - start
            total = total + diff
        print("{:.2f}s for {} iterations. {:d} refreshs per second"
              "".format(total, repeat, int(repeat/total)))
        self.clear_buffer()
        self.show()
