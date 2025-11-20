"""
constellation viewer
"""

import curses
import math
import time
from skyfield.api import Star, load, wgs84
from skyfield.data import hipparcos
from skyfield.projections import build_stereographic_projection

# configuration for ASCII art and camera
h = 24
w = 80
azimuth = 180.0 # all in degrees
alt = 30.0 
fov = 10.0 
scale = " .,:;+*#@"

# configuration for spaceslop
lat = 40.7128 # this is NYC btw
long = -74.0060

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.timeout(50)
    sh, sw = stdscr.getmaxyx() # fetch terminal size
    h = sh 
    w = sw 
    stdscr.addstr(h//2, w//2 - 26, "downloading planet data...")
    stdscr.refresh()

    # jpl ephemeris - https://ssd.jpl.nasa.gov/ephem.html
    ts = load.timescale()
    planets = load('de421.bsp')
    earth = planets['earth']
    observer = earth + wgs84.latlon(lat, long)
    bodies = { # celestial bodies that we will track
        'Mars': planets['mars'],
        'Venus': planets['venus'],
        'Jup': planets['jupiter barycenter'],
        'Sat': planets['saturn barycenter'],
        'Moon': planets['moon']
    }

    # star data from hipparicos - https://www.cosmos.esa.int/web/hipparcos/
    stdscr.clear()
    stdscr.addstr(h//2, w//2 - 24, "downloading star data...")
    stdscr.refresh()
    with load.open(hipparcos.URL) as f:
        df = hipparcos.load_dataframe(f)
    bright_stars = df[df['magnitude'] <= 3.5]
    stars = Star.from_dataframe(bright_stars)

    while True: # main drawing loop
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        t = ts.now()
        center_position = observer.at(t).from_altaz(alt_degrees=alt, az_degrees=azimuth)
        projection = build_stereographic_projection(center_position)

        # draw stars
        astrometric = observer.at(t).observe(stars)
        x_stars, y_stars = projection(astrometric)
        mags = bright_stars['magnitude'].values
        print(mags)

if __name__ == "__main__":
    curses.wrapper(main)