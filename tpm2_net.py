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

#Protocol Reference
#https://gist.github.com/jblang/89e24e2655be6c463c56

import socketserver
import apa102_matrix

class Tpm2NetServer(socketserver.UDPServer):

    def __init__(self):
        super().__init__(('', 65506), Tpm2NetHandler, bind_and_activate=True)
        self.matrix = apa102_matrix.Apa102Matrix()
        self.tmp_buffer = bytearray(self.matrix.num_rows * self.matrix.num_cols * 3)
        self.tmp_buffer_index = 0

class Tpm2NetHandler(socketserver.BaseRequestHandler):
  def handle(self):
    data = self.request[0].strip()
    data_length = len(data)
    socket = self.request[1]
    if not data_length >= 8 and data[0] == 0x9c: #packet start byte 0x9C
      return 
    #print("tpm2_net from {}:{}".format(self.client_address[0], self.client_address[1]))
    packet_type = data[1]
    frame_size = (data[2]<<8) + data[3]
    #print("framesize: {}".format(frame_size))
    if not (data_length - 7 == frame_size) and data[-1] == 0x36: #check consistency of length and proper frame ending
      return
    packet_number = data[4]
    number_of_packets = data[5]
    #print("packet: {}/{}".format(packet_number, number_of_packets))
    if packet_type == 0xDA: #data frame
        if packet_number == 1:
            self.server.tmp_buffer_index = 0
        self.server.tmp_buffer[self.server.tmp_buffer_index:self.server.tmp_buffer_index+frame_size] = data[6:-1]
        self.server.tmp_buffer_index = self.server.tmp_buffer_index + frame_size
        if packet_number == number_of_packets:
            self.server.matrix.set_rgb_buffer_with_flat_values(self.server.tmp_buffer)
            self.server.matrix.show()
            print(len(self.server.tmp_buffer))
    elif data[1] == 0xC0: #command
      #NOT IMPLEMENTED
      return
    elif data[1] == 0xAA: #request response
      #NOT IMPLEMENTED
      return
    else: # no valid tmp2 packet type
      return

if __name__ == "__main__":
    tpm2server = Tpm2NetServer()
    tpm2server.serve_forever()
    #tpm2server.server_close()
