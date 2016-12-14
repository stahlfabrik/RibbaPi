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

from PIL import Image
import time
import apa102_matrix

class PictureViewer:
    def __init__(self):
        self.matrix = apa102_matrix.Apa102Matrix()

    def convert_rgba_to_rgb(self, image, color=(0, 0, 0)):
        background = Image.new('RGB', image.size, color)
        background.paste(image, mask=image.split()[3])
        return background

    def convert_any_to_rgb(self, image):
        bands = image.getbands()
        if bands == ('R','G','B','A'):
            image = self.convert_rgba_to_rgb(image)
        elif bands != ('R','G','B'):
            image = im.convert('RGB')
        return image

    def resize_image(self, image, size):
        if image.size != size:
            image = image.resize(size)
        return image

    def display_image(self, filename):
        im = Image.open(filename)

        im = self.convert_any_to_rgb(im)
        im = self.resize_image(im, (self.matrix.num_cols, self.matrix.num_rows))

        self.matrix.set_rgb_buffer_with_flat_values(im.getdata())
        self.matrix.show(gamma=True)

    def display_gif(self, filename, repetitions=1):
        DEFAULT_FRAMES_PER_SEC = 25
        MAX_LENGTH_IN_SEC = 30
        FRAME_LIMIT = MAX_LENGTH_IN_SEC * DEFAULT_FRAMES_PER_SEC
        DEFAULT_DURATION = (1/DEFAULT_FRAMES_PER_SEC) * 1000
        MAX_DURATION = 5000
        try:
            im = Image.open(filename)
        except IOError:
            print("{} is not a valid image file".format(filename))
            return

        duration = DEFAULT_DURATION
        try:
            duration = int(im.info["duration"])
        except KeyError:
            print("filename has no duration in info.")
        except (TypeError, ValueError):
            print("cannot convert info[duration]: {} to int.".format(im.info[duration]))
        except:
            print("Unkown error")
            return

        if duration > MAX_DURATION:
            duration = DEFAULT_DURATION

        images_rgb_data = []

        more_frames = True
        while more_frames:
            frame = Image.new("RGBA", im.size)
            frame.paste(im)
            frame = self.convert_any_to_rgb(frame)
            frame = self.resize_image(frame, (self.matrix.num_cols, self.matrix.num_rows))
            frame_data = frame.getdata()
            try:
                im.seek(im.tell() + 1)
            except EOFError:
                more_frames = False
            images_rgb_data.append(frame_data)
            if len(images_rgb_data) > FRAME_LIMIT:
                break
        for i in range(repetitions):
            for frame_data in images_rgb_data:
                self.matrix.set_rgb_buffer_with_flat_values(frame_data)
                self.matrix.show(gamma=True)
                time.sleep(duration/1000)

    def show_sprite_sheet(self, filename, x, y, dx, dy, count, duration, repetitions):
        try:
            im = Image.open(filename)
        except IOError:
            print("{} is not a valid image file".format(filename))
            return
        im = self.convert_any_to_rgb(im)
        images_rgb_data = []
        for i in range(count):
            sprite = im.crop((x, y, x+dx, y+dy))
            sprite.load()
            sprite = self.resize_image(sprite, (self.matrix.num_cols, self.matrix.num_rows))
            frame_data = sprite.getdata()
            images_rgb_data.append(frame_data)
            x += dx
        for i in range(repetitions):
            for frame_data in images_rgb_data:
                self.matrix.set_rgb_buffer_with_flat_values(frame_data)
                self.matrix.show(gamma=True)
                time.sleep(duration/1000)

if __name__ == "__main__":
    pv = PictureViewer()
    pv.display_image("resources/batman-logo.png")
    time.sleep(2)
    pv.display_gif("resources/animations/gif/heart0.gif", 2)
    pv.display_gif("resources/animations/gif/heart3.gif", 2)
    pv.show_sprite_sheet("resources/mario_sprite_sheet.png", 96, 32, 16, 16, 3, 80, 10)
    pv.show_sprite_sheet("resources/mario_sprite_sheet.png", 96+64, 32, 16, 16, 1, 800, 1)
    pv.matrix.clear_rgb_buffer()
    pv.matrix.show()


