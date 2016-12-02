# RibbaPi
RibbaPi - APA102 based 16x16 LED-Matrix fitted inside Ribba picture frame, controlled by Raspberry Pi in Python

A YouTube video will be online in a few hours and will be linked here.

With RibbaPi I had the goal to build a programmable RGB LED matrix. I wanted to use APA102 leds - or Dotstars, as Adafruit calls them. Also, I wanted to control those with a Raspberry Pi, using only Python if that would be feasible. It turns out that it is. I also wanted the matrix to be 16x16 at least. Because I was a little afraid of the maximal power need of 60mA per LED (over 15A with 256 LEDs) plus the power the Raspberry Pi uses - I went with 16x16. It turns out that the process of building this project was fun but quite time consuming.

This are some, certainly not all, things that I used to build my RibbaPi matrix:
- Ikea Ribba picture frame 50x50cm
- 5m, white PCB, 60 LEDs/m APA102 strip
- Raspberry Pi 3 (if a Raspberry Pi Zero turns out to be powerfull enough - it would be cool to make that internal to the picture frame)
- 74AHCT125 level shifter
- raspberry pi prototyping hat for soldering the logic level converter circuit
- 488x488x3,2mm wood plate (HDF)
- 2,5mm^2 copper wire for the outer power rails
- 1,5mm^2 copper wire for each power row
- 0,8mm silver copper wire
- lots of hot glue
- lots of solder
- Meanwell LRS-100-5 power supply
- adequate power supply casing
- XT60 connectors
- switch and power plug
- some WAGO clamps
- 50x70cm 5mm white foam board
- adhesive plastic foil and 50x70cm sheet of architecture paper for light diffusion
- sharp knife (scalpel)
- soldering iron 25W
- cordless screwdriver with 1mm metal drill
- some heat shrink tubes
- USB cord to power Raspberry Pi (USB A side cut off)
- some more wires, plugs, fuse and stuff
- I did NOT use a capacitor as seems recommended in many WS2812b tutorials. With my power supply, the APA102 LEDs, the way of soldering EACH LED there seems no need to add an additional capacitor. Please correct me if I am wrong.





On the software side, this project has only started.
This is supported yet:
- configure the physical setup of your matrix design: origin location (top-left, top-right, buttom-left, buttom-right), wiring mode (zig-zag, row-by-row) and direction (horizontally, vertically)
- support for matrix sizes other then 16x16 should be working for the most parts
- 
TODO 

