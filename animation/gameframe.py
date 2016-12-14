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
    def __init__(self,  width, height, frame_queue, folder, play_for=10):
        super().__init__(width, height, frame_queue)
        self.folder = Path(folder).resolve()
        self.name = self.folder.name

        self.load_frames()
        self.read_config()

        if play_for == 0:
            self.duration = self.intrinsic_duration()
        else:
            self.duration = play_for

        print(self)

    def intrinsic_duration(self):
        # FIXME panoff needs accounting
        durX = 0
        if self.moveX > 0 and len(self.frames) > 0:
            durX = (self.frames[0].shape[1] / self.moveX) * self.hold / 1000
        durY = 0
        if self.moveY > 0 and len(self.frames) > 0:
            durY = (self.frames[0].shape[0] / self.moveY) * self.hold / 1000
        return max([len(self.frames)*self.hold/1000, durX, durY])

    def __str__(self):
        return "Path: {}\n"\
               "Name: {} frames: {} shape: {} duration: {}\n"\
               "hold: {} loop: {} moveX: {} moveY: {} moveloop: {} "\
               "panoff: {}\n"\
               "".format(self.folder,
                         self.name,
                         str(len(self.frames)),
                         self.frames[0].shape if len(self.frames) else
                         "no frames available",
                         self.duration,
                         self.hold,
                         self.loop,
                         self.moveX,
                         self.moveY,
                         self.move_loop,
                         self.panoff)

    def animate(self):
        while self.running:
            for frame in self.rendered_frames():
                self.frame_queue.put(frame.copy())
                time.sleep(self.hold/1000)
                if (time.time() - self.started) > self.duration:
                    break
            self.running = False

    def load_frames(self):
        self.frames = []
        for bmp in list(sorted(self.folder.glob("*.bmp"),
                               key=lambda bmpfile: int(bmpfile.stem))):
            im = Image.open(str(bmp))
            self.frames.append(np.array(im))

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
                    if self.move_loop:
                        x = 0

                if (self.moveY > 0 and (cur_y + DY) >= h) or \
                   (self.moveY < 0 and cur_y <= 0):
                    if self.move_loop:
                        y = 0

                if i == end:
                    if self.loop or self.move_loop:
                        i = 0
                    else:
                        break

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
