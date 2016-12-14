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



from animation.gameframe import GameframeAnimation
from pathlib import Path
from queue import Queue
import random
import time

#TODO
#Animations umbauen auf Queue
#Animations umbauen auf Abstract

DISPLAY_WIDTH = 16
DISPLAY_HEIGTH = 16
HARDWARE = "COMPUTER"


class RibbaPi():
    def __init__(self):
        if HARDWARE == 'APA102':
            from display.apa102 import Apa102
            self.display = Apa102(DISPLAY_WIDTH, DISPLAY_HEIGTH)
        elif HARDWARE == 'COMPUTER':
            from display.computer import Computer
            self.display = Computer(DISPLAY_WIDTH, DISPLAY_HEIGTH)
        else:
            raise RuntimeError(
                "Display hardware \"{}\" not known.".format(HARDWARE))

        self.current_animation = None
        self.frame_queue = Queue(maxsize=1)
        self.refresh_animations()

    def refresh_animations(self):
        # gameframe
        self.gameframe_animations = []
        for p in Path("resources/animations/gameframe/").resolve().glob("walker"):
            if p.is_dir():
                self.gameframe_animations.append(str(p))

    def clean_finished_animation(self):
        if self.current_animation and not self.current_animation.is_alive():
            self.current_animation = None

    def get_next_animation(self):
        i = random.randint(0, len(self.gameframe_animations) - 1)
        return GameframeAnimation(DISPLAY_WIDTH, DISPLAY_HEIGTH, self.frame_queue,
                                  self.gameframe_animations[i])

    def mainloop(self):
        while True:
            if not self.frame_queue.empty():
                #get frame and display it
                self.display.buffer = self.frame_queue.get()
                self.display.show(gamma=True)

            self.clean_finished_animation()

            if not self.current_animation:
                self.current_animation = self.get_next_animation()
                self.current_animation.start()

            time.sleep(1/60)




if __name__ == "__main__":
    ribbapi = RibbaPi()
    ribbapi.mainloop()
