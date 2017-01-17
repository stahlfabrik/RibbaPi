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
This module implements a display consisting of APA102 leds.
"""

import spidev
import time
import numpy as np
from enum import Enum

from display.abstract_display import AbstractDisplay


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


# class Singleton(type):
#     instance = None
#
#     def __call__(cls, *args, **kw):
#         if not cls.instance:
#             cls.instance = super(Singleton, cls).__call__(*args, **kw)
#         return cls.instance


SPI_MAX_SPEED_HZ = 16000000  # 500000 is default
DEFAULT_BRIGHTNESS = 31  # max: 31
DEFAULT_GAMMA = 2.22


# class Apa102(AbstractDisplay, metaclass=Singleton):
class Apa102(AbstractDisplay):
    def __init__(self, width=16, height=16, color_type=ColorType.bgr,
                 wire_mode=WireMode.zig_zag, origin=Origin.top_left,
                 orientation=Orientation.vertically):
        super().__init__(width, height)

        # init SPI interface
        self.spi = spidev.SpiDev()
        self.spi.open(0, 1)
        self.spi.max_speed_hz = SPI_MAX_SPEED_HZ

        # setup hardware and wiring related parameters
        self.color_type = color_type
        self.wire_mode = wire_mode
        self.origin = origin
        self.orientation = orientation

        # setup apa102 protocol stuff
        self.__start_frame = [0] * 4
        # end frame is >= (n/2) bits of 1, where n is the number of LEDs
        self.__end_frame = [0xff] * ((self.num_pixels + 15) // (2 * 8))
        self.__led_frame_start = 0b11100000

        # setup datastructures for fast lookup of led
        # led index for given coordinate
        (self.__pixel_coord_to_led_index,
         self.__virtual_to_physical_byte_indices) = \
            self.__create_pixel_to_led_index_datastructures()

        # create gamma correction values
        self.gamma = DEFAULT_GAMMA
        self.__gamma8 = self.get_gamma8_array(self.gamma)

        self.show()

    @staticmethod
    def get_gamma8_array(gamma):
        gamma8 = np.zeros((256,), dtype=np.uint8)
        for i in np.arange(256, dtype=np.uint8):
            gamma8[i] = (255 * ((i/255)**gamma) + 0.5).astype(np.uint8)
        return gamma8

    def __create_pixel_to_led_index_datastructures(self):
        pixel_coord_to_led_index = np.zeros((self.height, self.width),
                                            dtype=np.int)
        virtual_to_physical_byte_indices = np.zeros((self.height,
                                                     self.width,
                                                     4), dtype=np.int)

        outer, inner = (self.height, self.width) if \
            self.orientation == Orientation.horizontally else \
                       (self.width, self.height)
        current_outer_count = 0
        outer_range = range(outer)
        if (self.orientation == Orientation.horizontally and
           (self.origin == Origin.bottom_left or
                self.origin == Origin.bottom_right)) \
                or \
           (self.orientation == Orientation.vertically and
           (self.origin == Origin.top_right or
                self.origin == Origin.bottom_right)):
            outer_range = reversed(outer_range)
        for i in outer_range:
            current_inner_count = 0
            for j in range(inner):
                mod = (0 if self.orientation == Orientation.horizontally and
                       ((self.origin == Origin.bottom_left and
                        outer % 2 == 0) or
                        (self.origin == Origin.bottom_right and
                        outer % 2 == 1) or
                        self.origin == Origin.top_right)
                       or
                       self.orientation == Orientation.vertically and
                       ((self.origin == Origin.top_right and
                        outer % 2 == 0) or
                        (self.origin == Origin.bottom_right and
                         outer % 2 == 1) or
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
                coordinate = (i, current_inner_count) if \
                    self.orientation == Orientation.horizontally else \
                             (current_inner_count, i)
                pixel_coord_to_led_index[coordinate] = led_index
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

        for pixel_index in range(self.height * self.width):
                # for each pixel in buffer
                # calulate byte indices of pixel
                pixel_index_spread = pixel_index * 4  # room for byte led,r,g,b
                pixel_bytes_indices = [pixel_index_spread,
                                       pixel_index_spread + red,
                                       pixel_index_spread + green,
                                       pixel_index_spread + blue]

                # get coordinate of ith pixel
                pixel_row = pixel_index // self.width
                pixel_col = pixel_index - pixel_row * self.width

                # get led index of led at pixel coordinate
                led_index = pixel_coord_to_led_index[(pixel_row, pixel_col)]

                # get coordinate of ith led
                led_row = led_index // self.width
                led_col = led_index - led_row * self.width

                # set the transformation matrix accordingly
                virtual_to_physical_byte_indices[(led_row, led_col)] = \
                    pixel_bytes_indices

        return pixel_coord_to_led_index, virtual_to_physical_byte_indices

    def __str__(self):
        header = "APA102-matrix configuration: width: {} height: {} "\
                 "colortype: {} wiremode: {} origin: {} orientation {}\n"\
                 "".format(self.width,
                           self.height,
                           self.color_type,
                           self.wire_mode,
                           self.origin,
                           self.orientation)
        ret = header + "-"*len(header) + "\n"
        ret += '\t' + '\t'.join(map(str, list(range(self.width)))) + "\n"
        for i in range(self.height):
            ret += "{}\t".format(i)
            for j in range(self.width):
                ret += "{}\t".format(self.__pixel_coord_to_led_index[i, j])
            ret += "\n"
        return ret

    def get_brightness_array(self):
        brightness = DEFAULT_BRIGHTNESS
        if brightness < 0:
            brightness = 0
        if brightness > 31:
            brightness = 31
        led_frame_first_byte = \
            (brightness & ~self.__led_frame_start) | self.__led_frame_start
        ret = np.array([led_frame_first_byte] * self.num_pixels,
                       dtype=np.uint8)
        return ret.reshape((self.height, self.width, 1))

    def gamma_correct_buffer(self):
        for x in np.nditer(self._buffer,
                           op_flags=['readwrite'],
                           flags=['external_loop', 'buffered'],
                           order='F'):
            x[...] = self.__gamma8[x]

    def show(self, gamma=False):
        if gamma:
            self.gamma_correct_buffer()
        apa102_led_frames = np.concatenate((self.get_brightness_array(),
                                            self._buffer), axis=2)
        reindexed_frames = apa102_led_frames.take(
                                       self.__virtual_to_physical_byte_indices)
        to_send = \
            self.__start_frame \
            + reindexed_frames.flatten().tolist() \
            + self.__end_frame
        self.spi.writebytes(to_send)


if __name__ == "__main__":
    matrix = Apa102()
    print(matrix)

    matrix.run_benchmark()
    matrix.run_benchmark(gamma=True)

    matrix.create_test_pattern()
    matrix.show(gamma=False)
    time.sleep(5)
    matrix.create_test_pattern()
    matrix.show(gamma=True)
    time.sleep(5)

    matrix.clear_buffer()
    matrix.show()

    import random
    try:
        while(1):
            x = random.randint(0, 15)
            y = random.randint(0, 15)
            red = random.randint(0, 255)
            green = random.randint(0, 255)
            blue = random.randint(0, 255)
            matrix.set_pixel_at_coord(x, y, (red, green, blue))
            matrix.show(gamma=True)
    except KeyboardInterrupt:
        pass
    matrix.clear_buffer()
    matrix.show()
