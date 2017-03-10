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

# Notes
# find . -name \*.pyc -delete

from animation.gameframe import GameframeAnimation
from animation.blm import BlmAnimation
from animation.text import TextAnimation
from animation.clock import ClockAnimation
from animation.moodlight import MoodlightAnimation
from server.ribbapi_http import RibbaPiHttpServer
from server.tpm2_net import Tpm2NetServer

from pathlib import Path
import os
import queue
import random
import time
import threading

#TODO/Ideas
## add timer that displays a textmessage from predined list of messages
# restructure other animations

# make mood light animation

# add config file and argparsing of it

# sort animations case insensitive

DISPLAY_WIDTH = 16
DISPLAY_HEIGTH = 16
HARDWARE = "APA102"
#HARDWARE = "COMPUTER"


class RibbaPi():
    def __init__(self):
        os.chdir(os.path.dirname(__file__))

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
        self.receiving_data = threading.Event()

        self.gameframe_activated = False
        self.gameframe_repeat = -1
        self.gameframe_duration = 5
        self.gameframe_selected = []

        self.blm_activated = False
        self.blm_repeat = -1
        self.blm_duration = 5
        self.blm_selected = []

        self.clock_activated = False
        self.clock_last_shown = time.time()
        self.clock_show_every = 300
        self.clock_duration = 10

        self.moodlight_activated = True

        # find and prepare installed animations
        self.refresh_animations()

        self.play_random = False
        self.animations = self.animation_generator()

        # start http server
        self.http_server = RibbaPiHttpServer(self)
        self.http_server_thread = \
            threading.Thread(target=self.http_server.serve_forever,
                             daemon=True)
        self.http_server_thread.start()

        # start tpm2_net server
        self.tpm2_net_server = Tpm2NetServer(self)
        self.tpm2_net_server_thread = \
            threading.Thread(target=self.tpm2_net_server.serve_forever,
                             daemon=True)
        self.tpm2_net_server_thread.start()

        #self.text_queue.put("RibbaPi 👍")

    # New frame handling
    def process_frame_queue(self):
        # check if there is a frame that needs to be displayed
        if not self.frame_queue.empty():
            # get frame and display it
            self.display.buffer = self.frame_queue.get()
            self.frame_queue.task_done()
            self.display.show(gamma=True)

    # Text handling
    def process_text_queue(self):
        # check if external data (e.g. tpm2_net) is received
        if self.receiving_data.is_set():
            return
        # Prevent potential new text to interrupt current text animation
        if isinstance(self.current_animation, TextAnimation):
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
    def refresh_animations(self):
        # gameframe
        self.gameframe_animations = []
        for p in sorted(Path("resources/animations/gameframe/").glob("*")):
            if p.is_dir():
                self.gameframe_animations.append(str(p))
        for p in sorted(Path("resources/animations/gameframe_forum/").glob("*")):
            if p.is_dir():
                self.gameframe_animations.append(str(p))
        self.gameframe_selected = self.gameframe_animations.copy()

        # blm
        self.blm_animations = []
        for p in sorted(Path("resources/animations/162-blms/").glob("*.blm")):
            if p.is_file():
                self.blm_animations.append(str(p))
        self.blm_selected = self.blm_animations.copy()

    def clean_finished_animation(self):
        if self.current_animation and not self.current_animation.is_alive():
            self.current_animation = None

    def animation_generator(self):
        gameframes = self.gameframe_generator()
        blms = self.blm_generator()
        while True:
            if self.gameframe_activated:
                yield next(gameframes)
            if self.blm_activated:
                yield next(blms)
            if not (self.gameframe_activated or self.blm_activated):
                yield None

    def gameframe_generator(self):
        i = -1
        while True:
            if len(self.gameframe_selected) > 0:
                if self.play_random:
                    i = random.randint(0, len(self.gameframe_selected) - 1)
                else:
                    i += 1
                    i %= len(self.gameframe_selected)
                yield GameframeAnimation(DISPLAY_WIDTH,
                                         DISPLAY_HEIGTH,
                                         self.frame_queue,
                                         self.gameframe_repeat,
                                         self.gameframe_selected[i])
            else:
                yield None

    def blm_generator(self):
        i = -1
        while True:
            if len(self.blm_selected) > 0:
                if self.play_random:
                    i = random.randint(0, len(self.blm_selected) - 1)
                else:
                    i += 1
                    i %= len(self.blm_selected)
                yield BlmAnimation(DISPLAY_WIDTH,
                                   DISPLAY_HEIGTH,
                                   self.frame_queue,
                                   self.blm_repeat,
                                   self.blm_selected[i])
            else:
                yield None

    def store_animation_for_resume(self, animation):
        self.interrupted_animation_class = type(animation)
        self.interrupted_animation_kwargs = animation.kwargs

    def get_next_animation(self):
        next_animation = None
        # check if there is an animation to resume
        if self.interrupted_animation_class:
            next_animation = self.interrupted_animation_class(
                **self.interrupted_animation_kwargs)
            self.interrupted_animation_class = None
            self.interrupted_animation_kwargs = None
        elif self.clock_activated and \
                (self.clock_last_shown + self.clock_show_every < time.time()):
            # it is time to show time again:
            next_animation = ClockAnimation(DISPLAY_WIDTH,
                                            DISPLAY_HEIGTH,
                                            self.frame_queue)
            self.clock_last_shown = time.time()
        elif self.moodlight_activated:
            next_animation = MoodlightAnimation(DISPLAY_WIDTH,
                                               DISPLAY_HEIGTH,
                                               self.frame_queue)
        else:
            next_animation = next(self.animations)
        return next_animation

    def is_current_animation_running(self):
        return True if self.current_animation and \
            self.current_animation.is_alive() else False

    def stop_current_animation(self, resume=False):
        if self.is_current_animation_running():
            if resume:
                self.store_animation_for_resume(self.current_animation)
            self.current_animation.stop()

    def check_current_animation_runtime(self):
        if self.is_current_animation_running():
            if self.receiving_data.is_set():
                self.stop_current_animation()
            if isinstance(self.current_animation, ClockAnimation):
                duration = self.clock_duration
                if self.current_animation.started + duration < time.time():
                    self.stop_current_animation()
            if isinstance(self.current_animation, GameframeAnimation):
                duration = max(self.gameframe_duration,
                               self.current_animation.intrinsic_duration())
                if self.current_animation.started + duration < time.time():
                    self.stop_current_animation()
            if isinstance(self.current_animation, BlmAnimation):
                duration = max(self.blm_duration,
                               self.current_animation.intrinsic_duration())
                if self.current_animation.started + duration < time.time():
                    self.stop_current_animation()


    def mainloop(self):
        # TODO start auto renewing timer for clock and predined texts

        try:
            while True:
                self.process_frame_queue()
                # if the current_animation is finished then cleanup
                self.clean_finished_animation()
                # check if there is text to display
                self.process_text_queue()
                # if there is currently no animation, start a new one
                # check if external data (e.g. tpm2_net) is received
                if not self.current_animation and not self.receiving_data.is_set():
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

        self.http_server.shutdown()
        self.http_server.server_close()


if __name__ == "__main__":
    ribbapi = RibbaPi()
    ribbapi.display.show()

    ribbapi.mainloop()
