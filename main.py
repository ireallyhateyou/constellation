"""
constellation viewer
"""

import curses
import math
import time
from skyfield.api import Star, load, wgs84
from skyfield.data import hipparcos
from skyfield.projections import build_stereographic_projection

# configuration for ASCII art
h = 24, w = 80
fov = 10 # degrees
scale = " .,:;+*#@"

# configuration for spaceslop
lat = 40.7128 # this is NYC btw
long = -74.0060

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.timeout(50)
    ts = load.timescale()
    # jpl ephemeris - https://ssd.jpl.nasa.gov/ephem.html
    planets = load('de421.bsp')
    earth = planets['earth']
    stdscr.addstr(h//2, w//2 - 10, "downloading star data...")
    stdscr.refresh()
    observer = earth + wgs84.latlon(lat, long)

if __name__ == "__main__":
    curses.wrapper(main)