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
    def __init__(self, width, height, frame_queue):
        super().__init__()
        self.width = width
        self.height = height
        self.frame_queue = frame_queue
        self.running = False

    def run(self):
        """This is the run method from threading.Thread"""
        self.running = True
        self.started = time.time()
        self.animate()

    # def start(self):
    """We do not overwrite this. It is from threading.Thread"""

    def stop(self):
        self.running = False

    @abc.abstractmethod
    def animate(self):
        """This is where frames are put to the frame_queue in correct time"""
