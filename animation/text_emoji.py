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

import freetype
import numpy as np
from PIL import Image
import time

import apa102_matrix

np.set_printoptions(threshold=np.nan, linewidth=240)

class TextAndEmojiViewer():
    def __init__(self, text_size=16, emoji_size=20, text_font="resources/fonts/helvetica.ttf", emoji_font="resources/fonts/Apple Color Emoji.ttc"):
        self.text_face = freetype.Face(text_font)
        self.emoji_face = freetype.Face(emoji_font)

        self.text_size = text_size
        self.text_face.set_char_size(self.text_size * 64)
        self.emoji_face.set_char_size(emoji_size * 64)

        self.matrix = apa102_matrix.Apa102Matrix()
    def __del__(self):
        del self.text_face
        del self.emoji_face

    def render(self, text):
        width, height, baseline = 0, 0, 0
        previous = 0

		# first pass
        for c in text:
            if self.text_face.get_char_index(c):
                self.text_face.load_char(c)
                glyph = self.text_face.glyph
                bitmap = glyph.bitmap
                height = max(height, bitmap.rows + max(0,-(glyph.bitmap_top-bitmap.rows)))
                baseline = max(baseline, max(0,-(glyph.bitmap_top-bitmap.rows)))
                kerning = self.text_face.get_kerning(previous, c)
                width += (glyph.advance.x >> 6) + (kerning.x >> 6)
                previous = c
            elif self.emoji_face.get_char_index(c):
                height = max(height, self.text_size)
                width += self.text_size + 1
                previous = 0
        print(width, height, baseline)

        buf = np.zeros((height,width,3), dtype=np.uint8)

        #second pass
        x, y = 0, 0
        previous = 0
        for c in text:
            if self.text_face.get_char_index(c):
                self.text_face.load_char(c)
                glyph = self.text_face.glyph
                bitmap = glyph.bitmap
                top = glyph.bitmap_top
                left = glyph.bitmap_left
                w,h = bitmap.width, bitmap.rows
                y = height - baseline - top
                kerning = self.text_face.get_kerning(previous, c)
                x += (kerning.x >> 6)
                char_buf = np.array(bitmap.buffer, dtype=np.uint8).reshape(h,w)
                buf[y:y+h,x:x+w] += np.repeat(char_buf,3,axis=1).reshape(h,w,3)
                x += (glyph.advance.x >> 6)
                previous = c
            elif self.emoji_face.get_char_index(c):
                y = 0
                h = self.text_size
                w = self.text_size
                char_buf = self.get_color_char(c)
                buf[y:y+h,x:x+w] += char_buf
                x += self.text_size + 1
                previous = 0
        return buf

    def get_color_char(self, char):
        self.emoji_face.load_char(char, freetype.FT_LOAD_COLOR)
        bitmap = self.emoji_face.glyph.bitmap
        bitmap = np.array(bitmap.buffer, dtype=np.uint8).reshape((bitmap.rows,bitmap.width,4))
        rgb = self.convert_bgra_to_rgb(bitmap)
        im = Image.fromarray(rgb)
        im = im.resize((self.text_size, self.text_size))
        return np.array(im)

    def convert_bgra_to_rgb(self, buf):
        blue = buf[:,:,0]
        green = buf[:,:,1]
        red = buf[:,:,2]
        return np.dstack((red, green, blue))

    def show_scrolling_text(self, text, steps_per_second=15, pixels_per_step=1):
        if steps_per_second <= 0 or pixels_per_step < 1:
            return
        buf = self.render(text)
        height, width, nbytes = buf.shape
        h_pad_0 = self.matrix.num_cols
        h_pad_1 = self.matrix.num_cols + pixels_per_step
        v_pad_0 = 0
        v_pad_1 = 0
        if height < self.matrix.num_rows:
            v_pad_0 = int((self.matrix.num_rows - height)/2)
            v_pad_1 = self.matrix.num_rows - height - v_pad_0

        buf = np.pad(buf, ((v_pad_0, v_pad_1), (h_pad_0, h_pad_1), (0,0)), 'constant', constant_values=0)
        wait = 1.0/steps_per_second

        for i in range(0, buf.shape[1] - self.matrix.num_cols, pixels_per_step):
            cut = buf[0:self.matrix.num_rows, i:i+self.matrix.num_cols, :]
            self.matrix.set_rgb_buffer_with_flat_values(cut.flatten())
            self.matrix.show(gamma=True)
            time.sleep(wait)

if __name__ == "__main__":
    text = "Hello YouTube!😎😜👍"
    #text = "AV,p!"
    t = TextAndEmojiViewer()
    t.show_scrolling_text(text)
