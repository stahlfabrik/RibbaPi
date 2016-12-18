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

from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib
import html


class RibbaPiHttpServer(HTTPServer):
    def __init__(self, text_queue):
        super().__init__(('', 8080), RibbaPiHttpHandler)
        self.text_queue = text_queue


class RibbaPiHttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write("""<html>
            <body>
            <h1>RibbaPi</h1>
            <h2>Text display</h2>
            <form action="api/v1/displaytext" method="post">
            <fieldset>
            <legend>Enter text to be displayed on RibbaPi</legend>
            <input type="text" name="message"><br>
            <input type="submit" value="Submit">
            </fieldset>
            </form>
            </body>
            </html>""".encode("utf-8"))


    def do_POST(self):
        if self.path.startswith("/api/v1/displaytext"):
            content_length = int(self.headers['Content-Length'])
            if self.headers['Content-Type'] == "application/x-www-form-urlencoded":
                post_data = self.rfile.read(content_length)
                post_data = str(post_data, 'utf-8')
                post_data_dict = urllib.parse.parse_qs(post_data)
                message = post_data_dict["message"][0]
                message = html.unescape(message)
                self.server.text_queue.put(message)
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write("""<html>
                <body>Message is now displayed on RibbaPi<br><br>
                <script>
                document.write('<a href="' + document.referrer + '">Go Back</a>');
                </script>
                </body>
                </html>""".encode("utf-8"))


if __name__ == "__main__":
    server = RibbaPiHttpServer()
    server.serve_forever()
