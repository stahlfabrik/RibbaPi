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
This module contains the Apa102Matrix class. This class is the low layer
representation of the APA102 based matrix.
"""

import spidev

import time

import numpy as np
from enum import Enum

SPI_MAX_SPEED_HZ = 16000000  # 500000 is default
DEFAULT_BRIGHTNESS = 5  # max: 31
DEFAULT_GAMMA = 2.22


class ColorType(Enum):
    rgb = 1
    rbg = 2
    grb = 3
    gbr = 4
    bgr = 5
    brg = 6


class WireMode(Enum):
    line_by_line = 1
    zig_zag = 2


class Orientation(Enum):
    horizontally = 1
    vertically = 2


class Origin(Enum):
    top_left = 1
    top_right = 2
    bottom_left = 3
    bottom_right = 4


class Singleton(type):
    instance = None

    def __call__(cls, *args, **kw):
        if not cls.instance:
            cls.instance = super(Singleton, cls).__call__(*args, **kw)
        return cls.instance


class Apa102Matrix(metaclass=Singleton):
    def __init__(self, num_rows=16, num_cols=16, color_type=ColorType.bgr,
                 wire_mode=WireMode.zig_zag, origin=Origin.bottom_left,
                 orientation=Orientation.horizontally):

        # init SPI interface
        self.spi = spidev.SpiDev()
        self.spi.open(0, 1)
        self.spi.max_speed_hz = SPI_MAX_SPEED_HZ

        # setup matrix parameters
        self.num_rows = num_rows
        self.num_cols = num_cols
        self.num_leds = self.num_rows * self.num_cols
        self.color_type = color_type
        self.wire_mode = wire_mode
        self.origin = origin
        self.orientation = orientation

        # setup apa102 protocol stuff
        self.__start_frame = [0] * 4
        # end frame is >= (n/2) bits of 1, where n is the number of LEDs
        self.__end_frame = [0xff] * ((self.num_leds + 15) // (2 * 8))
        self.__rgb_buffer = np.zeros((self.num_rows, self.num_cols, 3),
                                     dtype=np.uint8)  # 3 for red, green, blue
        self.__led_frame_start = 0b11100000

        # setup datastructures for fast lookup of led
        # led index for given coordinate
        self.__pixel_coord_to_led_index = \
            np.zeros((self.num_rows, self.num_cols), dtype=np.int)
        self.__virtual_to_physical_byte_indices = \
            np.zeros((self.num_rows, self.num_cols, 4), dtype=np.int)
        self.populate_pixel_to_led_index_datastructure()
        self.show()

        # Gamma Correction stuff
        self.gamma = DEFAULT_GAMMA
        self.__gamma8 = np.zeros((256,), dtype=np.uint8)
        self.populate_gamma_array()

    def populate_gamma_array(self):
        for i in np.arange(256, dtype=np.uint8):
            self.__gamma8[i] = \
                (255 * ((i/255)**(self.gamma)) + 0.5).astype(np.uint8)

    def populate_pixel_to_led_index_datastructure(self):
        outer, inner = (self.num_rows, self.num_cols) if self.orientation == Orientation.horizontally else (self.num_cols, self.num_rows)
        current_outer_count = 0
        outer_range = range(outer)
        if (self.orientation == Orientation.horizontally and (self.origin == Origin.bottom_left or self.origin == Origin.bottom_right)) or \
           (self.orientation == Orientation.vertically and (self.origin == Origin.top_right or self.origin == Origin.bottom_right)):
            outer_range = reversed(outer_range)
        for i in outer_range:
            current_inner_count = 0
            for j in range(inner):
                mod = (0 if self.orientation == Orientation.horizontally and ((self.origin == Origin.bottom_left and outer % 2 == 0) or
                                                                              (self.origin == Origin.bottom_right and outer % 2 == 1) or
                                                                               self.origin == Origin.top_right)
                            or
                            self.orientation == Orientation.vertically and ((self.origin == Origin.top_right and outer % 2 == 0) or
                                                                            (self.origin == Origin.bottom_right and outer % 2 == 1) or
                                                                             self.origin == Origin.bottom_left)
                         else 1)
                if (self.wire_mode == WireMode.zig_zag and i % 2 == mod) or \
                   (self.wire_mode == WireMode.line_by_line and
                       ((self.orientation == Orientation.horizontally and
                           (self.origin == Origin.bottom_right or
                            self.origin == Origin.top_right))
                         or
                        (self.orientation == Orientation.vertically and
                            (self.origin == Origin.bottom_left or
                             self.origin == Origin.bottom_right)))):
                    j = (inner - 1) - current_inner_count
                led_index = j + current_outer_count * inner
                self.__pixel_coord_to_led_index[(i, current_inner_count) if
                        self.orientation == Orientation.horizontally else
                        (current_inner_count, i)] = led_index
                current_inner_count += 1
            current_outer_count += 1

        if self.color_type == ColorType.rgb:
            red, green, blue = 1, 2, 3
        elif self.color_type == ColorType.rbg:
            red, green, blue = 1, 3, 2
        elif self.color_type == ColorType.grb:
            red, green, blue = 2, 1, 3
        elif self.color_type == ColorType.gbr:
            red, green, blue = 3, 1, 2
        elif self.color_type == ColorType.bgr:
            red, green, blue = 3, 2, 1
        elif self.color_type == ColorType.brg:
            red, green, blue = 2, 3, 1

        for i in range(self.num_rows):
            for j in range(self.num_cols):
                col_index = (self.num_cols - 1) - j
                led_index = self.__pixel_coord_to_led_index[i, col_index] * 4
                self.__virtual_to_physical_byte_indices[i, j] = \
                    [led_index,
                     led_index + red,
                     led_index + green,
                     led_index + blue]

    def __str__(self):
        header = "APA102-matrix configuration: rows: {} cols: {} "\
                 "colortype: {} wiremode: {} origin: {} orientation {}\n"\
                 "".format(self.num_rows,
                           self.num_cols,
                           self.color_type,
                           self.wire_mode,
                           self.origin,
                           self.orientation)
        ret = header + "-"*len(header) + "\n"
        ret += '\t' + '\t'.join(map(str, list(range(self.num_cols)))) + "\n"
        for i in range(self.num_rows):
            ret += "{}\t".format(i)
            for j in range(self.num_cols):
                ret += "{}\t".format(self.__pixel_coord_to_led_index[i, j])
            ret += "\n"
        return ret

    def clear_rgb_buffer(self):
        self.__rgb_buffer = np.zeros_like(self.__rgb_buffer)

    def get_brightness_array(self):
        brightness = DEFAULT_BRIGHTNESS
        if brightness < 0:
            brightness = 0
        if brightness > 31:
            brightness = 31
        led_frame_first_byte = \
            (brightness & ~self.__led_frame_start) | self.__led_frame_start
        ret = np.array([led_frame_first_byte] * self.num_leds, dtype=np.uint8)
        return ret.reshape((self.num_rows, self.num_cols, 1))

    def gamma_correct(self):
        for x in np.nditer(self.__rgb_buffer,
                           op_flags=['readwrite'],
                           flags=['external_loop', 'buffered'],
                           order='F'):
            x[...] = self.__gamma8[x]

    def show(self, gamma=False):
        if gamma:
            self.gamma_correct()
        apa102_led_frames = np.concatenate((self.get_brightness_array(),
                                            self.__rgb_buffer), axis=2)
        reindexed_frames = apa102_led_frames.take(
                                       self.__virtual_to_physical_byte_indices)
        to_send = \
            self.__start_frame \
            + reindexed_frames.flatten().tolist() \
            + self.__end_frame
        self.spi.writebytes(to_send)

    def set_pixel_at_index(self, index, red, green, blue):
        if (index < 0) or (index >= self.num_leds):
            return
        index *= 3
        self.__rgb_buffer.put([index, index+1, index+2], [red, green, blue])

    def set_pixel_at_coord(self, x, y, red, green, blue):
        if (x < 0) or (x >= self.num_cols) or (y < 0) or (y >= self.num_rows):
            return
        self.__rgb_buffer[y, x] = [red, green, blue]

    def set_rgb_buffer_with_flat_values(self, rgb_values):
        try:
            rgb_values = np.array(rgb_values, dtype=np.uint8)
            rgb_values.resize((self.num_leds * 3,))
            rgb_values = rgb_values.reshape(self.num_rows, self.num_cols, 3)
        except:
            return
        self.__rgb_buffer = rgb_values

    def show_test_pattern(self, gamma=False):
        self.clear_rgb_buffer()
        values = np.arange(0, 256, int(256/(self.num_cols-1)), dtype=np.uint8)
        self.__rgb_buffer[0:self.num_cols/4*1, :, 0:3] = \
            self.__rgb_buffer[0:4, :, 0:3] + \
            np.resize(values, (3, self.num_cols)).transpose()
        self.__rgb_buffer[self.num_cols/4*1:self.num_cols/4*2, :, 0] += values
        self.__rgb_buffer[self.num_cols/4*2:self.num_cols/4*3, :, 1] += values
        self.__rgb_buffer[self.num_cols/4*3:self.num_cols/4*4, :, 2] += values
        self.show(gamma)

    def benchmark(self, gamma=False):
        total = 0
        repeat = self.num_leds * 10
        for i in range(repeat):
            start = time.time()
            self.set_pixel_at_index(i % matrix.num_leds, 255, 255, 255)
            self.show(gamma)
            self.clear_rgb_buffer()
            end = time.time()
            diff = end - start
            total = total + diff
        print("{:.2f}s for {} iterations. {:d} refreshs per second"
              "".format(total, repeat, int(repeat/total)))
        self.clear_rgb_buffer()
        self.show()


if __name__ == "__main__":
    matrix = Apa102Matrix()
    matrix.benchmark()
    matrix.benchmark(gamma=True)
    matrix.show_test_pattern()
    time.sleep(5)
    matrix.show_test_pattern(gamma=True)
    time.sleep(5)

    matrix.clear_rgb_buffer()
    matrix.show()

    import random
    try:
        while(1):
            x = random.randint(0, 15)
            y = random.randint(0, 15)
            red = random.randint(0, 255)
            green = random.randint(0, 255)
            blue = random.randint(0, 255)
            matrix.set_pixel_at_coord(x, y, red, green, blue)
            matrix.show(gamma=0.35)
    except KeyboardInterrupt:
        pass
    matrix.clear_rgb_buffer()
    matrix.show()
