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
This is the sceleton code for all animations.
"""

import abc
import threading
import time


class AbstractAnimation(abc.ABC, threading.Thread):
    def __init__(self, width, height, frame_queue, repeat):
        super().__init__(daemon=True)
        self.width = width  # width of frames to produce
        self.height = height  # height of frames to produce
        self.frame_queue = frame_queue  # queue to put frames onto
        self.repeat = repeat  # 0: no repeat, -1: forever, > 0: x-times

        self._running = False  # query this often! exit self.animate quickly

    def run(self):
        """This is the run method from threading.Thread"""
        #TODO threading.Barrier to sync with ribbapi
        #print("Starting")

        self.started = time.time()
        self._running = True
        self.animate()

    # def start(self):
    """We do not overwrite this. It is from threading.Thread"""

    def stop(self):
        self._running = False

    @abc.abstractmethod
    def animate(self):
        """This is where frames are put to the frame_queue in correct time"""

    @property
    @abc.abstractmethod
    def kwargs(self):
        """This method must return all init args to be able to create identical
        animation. Repeat should reflect current repeats left."""

    # @property
    # @abc.abstractmethod
    # def intrinsic_duration(self):
    #     """This method should return the duration for one run of the animation,
    #     based on frame count and duration of each frame. In milliseconds.
    #     Return -1 for animations that do not have an intrinsic_duration. The
    #     basic idea is to let animations run for only a default amount of time.
    #     Longer animations should be supported by asking for their intrinsic
    #     duration. Of course repeats must be set to 0 then."""
