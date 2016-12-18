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
from animation.text import TextAnimation
from server.ribbapi_http import RibbaPiHttpServer

from pathlib import Path
import queue
import random
import time
import threading

#TODO
# change repeat logic for animation 0==no repeat -1=infinite x=x repeats
# change get next animation: should be able to
## get random animation
## get next animation from list
## narrow selection to certain animations

# store reference to interrupted animation (for resume)
#add queue for text to display
## write http server that provides REST API for text messages
## write http server that provides a form to enter a text messages
## add timer that displays a textmessage from predined list of messages
## make textviewer an animation? Make it interrupt running animations
# add tpm2net server. It must be able to interrupt everything else. But Maybe text should interrupt.
# Make clock an animation and setup a timer that brings clock on display.
# restructure other animations

DISPLAY_WIDTH = 16
DISPLAY_HEIGTH = 16
#HARDWARE = "APA102"
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

        self.interrupted_animation_class = None
        self.interrupted_animation_kwargs = None

        self.frame_queue = queue.Queue(maxsize=1)
        self.text_queue = queue.Queue()

        self.gameframe_activated = True
        self.gameframe_duration = 30

        self.refresh_animations()

        self.http_server = RibbaPiHttpServer(self.text_queue)
        self.http_server_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
        self.http_server_thread.start()

        #self.text_queue.put("RibbaPi 👍")

    # New frame handling
    def process_frame_queue(self):
        # check if there is a frame that needs to be displayed
        if not self.frame_queue.empty():
            # get frame and display it
            self.display.buffer = self.frame_queue.get()
            self.display.show(gamma=True)

    # Text handling
    def process_text_queue(self):
        # Prevent potential new text to interrupt current text animation
        if self.check_current_animation_type("text"):
            return
        # check if there is a string waiting to be displayed
        if not self.text_queue.empty():
            # interrupt current_animation
            self.stop_current_animation(resume=True)
            # return to come back and go on when current_animation is finished
            if self.is_current_animation_running():
                return
            # get text and create text animation
            text = self.text_queue.get()
            self.current_animation = TextAnimation(DISPLAY_WIDTH,
                                                   DISPLAY_HEIGTH,
                                                   self.frame_queue,
                                                   False,
                                                   text)
            self.current_animation.start()

    # Animation handling
    def check_current_animation_type(self, typestr):
        # check animation.name if it starts with type
        # known types "gameframe., bml., clock., text., maybe tpm2net"
        return True if self.current_animation and \
            self.current_animation.name.startswith(typestr) else False

    def refresh_animations(self):
        # gameframe
        self.gameframe_animations = []
        for p in sorted(Path("resources/animations/gameframe/").resolve().glob("*")):
            if p.is_dir():
                self.gameframe_animations.append(str(p))

    def clean_finished_animation(self):
        if self.current_animation and not self.current_animation.is_alive():
            self.current_animation = None

    def get_next_animation(self):
        # check if there is an animation to resume
        if self.interrupted_animation_class:
            resumed = self.interrupted_animation_class(**self.interrupted_animation_kwargs)
            self.interrupted_animation_class = None
            self.interrupted_animation_kwargs = None
            return resumed
        if self.gameframe_activated:
            i = random.randint(0, len(self.gameframe_animations) - 1)
            return GameframeAnimation(DISPLAY_WIDTH, DISPLAY_HEIGTH,
                                      self.frame_queue,
                                      True,
                                      self.gameframe_animations[i])

    def is_current_animation_running(self):
        return True if self.current_animation and \
            self.current_animation.is_alive() else False

    def stop_current_animation(self, resume=False):
        if self.is_current_animation_running():
            if resume:
                self.interrupted_animation_class = type(self.current_animation)
                self.interrupted_animation_kwargs = self.current_animation.get_kwargs()
            self.current_animation.stop()

    def check_current_animation_runtime(self):
        if self.is_current_animation_running():
            if self.check_current_animation_type("gameframe"):
                #TODO get intrinsic_duration
                duration = self.gameframe_duration
                if self.current_animation.started + duration < time.time():
                    self.stop_current_animation()

    def mainloop(self):
        # TODO start auto renewing timer for clock and predined texts
        try:
            while True:
                self.process_frame_queue()

                # if the current_animation is finished then cleanup
                self.clean_finished_animation()

                # TODO if there is text to display, show it - interrupt
                # current animation. When done, resume would be cool.
                self.process_text_queue()

                # TODO if the tpm2net server is receiving frames then stop everything
                # else and let it put frames to the queue

                # if there is currently no animation, start a new one
                if not self.current_animation:
                    self.current_animation = self.get_next_animation()
                    if self.current_animation:
                        self.current_animation.start()

                # Check if current_animation has played long enough
                self.check_current_animation_runtime()

                # to limit CPU usage do not go faster than 60 "fps"
                time.sleep(1/60)
        except KeyboardInterrupt:
            pass

        self.stop_current_animation()
        self.display.clear_buffer()
        self.display.show()


if __name__ == "__main__":
    ribbapi = RibbaPi()
    ribbapi.mainloop()
