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
from PIL import Image

import configparser
from pathlib import Path

from animation.abstract_animation import AbstractAnimation

# TODO: Subfolders have not been implemented yet.


class GameframeAnimation(AbstractAnimation):
    def __init__(self, width, height, frame_queue, repeat, folder):
        super().__init__(width, height, frame_queue, repeat)
        self.folder = Path(folder)
        if not self.folder.is_dir():
            raise NotADirectoryError
        self.name = "gameframe.{}".format(self.folder.name)

        self.load_frames()
        self.read_config()

        if not (self.loop or self.move_loop):
            self.repeat = 0

        print(self.name, self.intrinsic_duration())

    def intrinsic_duration(self):
        return sum(1 for _ in self.rendered_frames()) * self.hold/1000

    def __str__(self):
        return "Path: {}\n"\
               "Name: {} frames: {} shape: {}\n"\
               "hold: {} loop: {} moveX: {} moveY: {} moveloop: {} "\
               "panoff: {}\n"\
               "".format(self.folder,
                         self.name,
                         str(len(self.frames)),
                         self.frames[0].shape if len(self.frames) else
                         "no frames available",
                         self.hold,
                         self.loop,
                         self.moveX,
                         self.moveY,
                         self.move_loop,
                         self.panoff)

    def load_frames(self):
        self.frames = []
        for path in list(sorted(self.folder.glob("*.bmp"),
                                key=lambda bmpfile: int(bmpfile.stem))):
            with open(str(path), 'rb') as f:
                image = Image.open(f)
                self.frames.append(np.array(image))
            image = None
        if len(self.frames) == 0:
            raise AttributeError

    def read_config(self):
        self.hold = 100
        self.loop = True
        self.moveX = 0
        self.moveY = 0
        self.move_loop = False
        self.panoff = False
        self.nextFolder = None

        config = self.folder.joinpath("config.ini")
        if config.is_file():
            parser = configparser.ConfigParser()
            parser.read(str(config))
            self.hold = int(parser.get('animation', 'hold', fallback='100'))
            self.loop = parser.getboolean('animation', 'loop', fallback=True)
            self.moveX = int(parser.get('translate', 'moveX', fallback='0'))
            self.moveY = int(parser.get('translate', 'moveY', fallback='0'))
            self.move_loop = \
                parser.getboolean('translate', 'loop', fallback=False)
            self.panoff = \
                parser.getboolean('translate', 'panoff', fallback=False)
            self.nextFolder = \
                parser.getboolean('translate', 'nextFolder', fallback=None)

    def rendered_frames(self):
        """Generator function to iterate through all frames of animation"""
        i = 0
        end = len(self.frames)

        x = 0
        y = 0
        DX = self.width
        DY = self.height

        if end:
            while True:
                frame = self.frames[i]
                if self.panoff:
                    if self.moveX != 0:
                        (h, w, b) = frame.shape
                        frame = np.pad(frame,
                                       ((0, 0), (w, w), (0, 0)),
                                       'constant', constant_values=0)
                    if self.moveY != 0:
                        (h, w, b) = frame.shape
                        frame = np.pad(frame,
                                       ((h, h), (0, 0), (0, 0)),
                                       'constant', constant_values=0)
                (h, w, b) = frame.shape
                if self.moveX >= 0:
                    cur_x = w - DX - x
                else:
                    cur_x = x
                if self.moveY >= 0:
                    cur_y = y
                else:
                    cur_y = h - DY - y

                yield frame[cur_y:cur_y+DY, cur_x:cur_x+DX, :]

                i += 1
                x += abs(self.moveX)
                y += abs(self.moveY)

                if (self.moveX > 0 and cur_x <= 0) or \
                   (self.moveX < 0 and cur_x >= (w - DX)):
                    break
                    # if self.move_loop:
                    #     x = 0

                if (self.moveY > 0 and (cur_y + DY) >= h) or \
                   (self.moveY < 0 and cur_y <= 0):
                    # if self.move_loop:
                    #     y = 0
                    break

                # if i == end:
                #     if self.loop or self.move_loop:
                #         i = 0
                #     else:
                #         break
                if i == end:
                    if ((self.loop or self.move_loop) and
                        (((self.moveX > 0 and cur_x > 0) or
                          (self.moveX < 0 and cur_x < (w - DX))) or
                         ((self.moveY > 0 and (cur_y + DY) < h) or
                          (self.moveY < 0 and cur_y > 0)))):
                        i = 0
                    else:
                        break

    def animate(self):
        while self._running:
            for frame in self.rendered_frames():
                if self._running:
                    self.frame_queue.put(frame.copy())
                else:
                    break
                time.sleep(self.hold/1000)
                # if (time.time() - self.started) > self.duration:
                #     break
            if self.repeat > 0:
                self.repeat -= 1
            elif self.repeat == 0:
                self._running = False

    @property
    def kwargs(self):
        return {"width": self.width, "height": self.height,
                "frame_queue": self.frame_queue, "repeat": self.repeat,
                "folder": self.folder}
