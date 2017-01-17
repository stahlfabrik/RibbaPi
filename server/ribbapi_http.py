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
    def __init__(self, ribbapi):
        super().__init__(('', 8080), RibbaPiHttpHandler)
        self.ribbapi = ribbapi


class RibbaPiHttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write("""<html>
            <head><title>RibbaPi Control</title><meta charset="UTF-8"></head>
            <body>
            <h1>RibbaPi</h1>
            <h2>Text display</h2>
            <form action="api/v1/displaytext" method="post">
            <fieldset>
            <legend>Enter text to be displayed on RibbaPi</legend>
            <input type="text" name="message"><br>
            <input type="submit" value="Submit">
            </fieldset>
            </form>""".encode("utf-8"))
            self.wfile.write("""<h2>Animations</h2>
            <form action="api/v1/setgameframe" method="post">
            <fieldset>
            <legend>Choose gameframe animations to display</legend>""".encode("utf-8"))
            for animation in self.server.ribbapi.gameframe_animations:
                self.wfile.write("""<input type="checkbox"
                                            name="animations"
                                            value="{}" {}> <a href="{}">{}</a><br>""".format(
                                            animation,
                                            "checked" if animation in self.server.ribbapi.gameframe_selected else "",
                                            "playnext/" + animation,
                                            animation).encode("utf-8"))
            self.wfile.write("""<input type="submit" value="Submit">
            </fieldset>
            </form>""".encode("utf-8"))
            self.wfile.write("</body></html>".encode("utf-8"))
        print(self.path)
        if self.path.startswith("/playnext"):
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()


    def do_POST(self):
        if self.path.startswith("/api/v1/displaytext"):
            content_length = int(self.headers['Content-Length'])
            if self.headers['Content-Type'] == "application/x-www-form-urlencoded":
                post_data = self.rfile.read(content_length)
                post_data = str(post_data, 'utf-8')
                post_data_dict = urllib.parse.parse_qs(post_data)
                post_data_dict = html.unescape(post_data_dict)
                message = post_data_dict["message"][0]
                self.server.ribbapi.text_queue.put(message)
                self.send_response(303)
                self.send_header('Location', '/')
                self.end_headers()
                # self.send_response(200)
                # self.send_header('Content-type', 'text/html')
                # self.end_headers()
                # self.wfile.write("""<html>
                # <body>Message is now displayed on RibbaPi<br><br>
                # <script>
                # document.write('<a href="' + document.referrer + '">Go Back</a>');
                # </script>
                # </body>
                # </html>""".encode("utf-8"))
        if self.path.startswith("/api/v1/setgameframe"):
            content_length = int(self.headers['Content-Length'])
            if self.headers['Content-Type'] == "application/x-www-form-urlencoded":
                post_data = self.rfile.read(content_length)
                post_data = str(post_data, 'utf-8')
                post_data_dict = urllib.parse.parse_qs(post_data)
                if "animations" in post_data_dict:
                    selected_animations = post_data_dict["animations"]
                    selected_animations = html.unescape(selected_animations)
                    self.server.ribbapi.gameframe_selected = selected_animations
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write("""<html>
                    <body>Gameframe animations set<br><br>
                    <script>
                    document.write('<a href="' + document.referrer + '">Go Back</a>');
                    </script>
                    </body>
                    </html>""".encode("utf-8"))
                else:
                    self.server.ribbapi.gameframe_selected = []
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write("""<html>
                    <body>Gameframe animations set<br><br>
                    <script>
                    document.write('<a href="' + document.referrer + '">Go Back</a>');
                    </script>
                    </body>
                    </html>""".encode("utf-8"))
