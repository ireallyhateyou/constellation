"""
constellation viewer
"""

import curses
import math
import time
from skyfield.api import Star, load, wgs84
from skyfield.data import hipparcos
from skyfield.projections import build_stereographic_projection

def main(stdscr):
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

    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.timeout(50)
    sh, sw = stdscr.getmaxyx() # fetch terminal size
    h = sh 
    w = sw 
    stdscr.addstr(h//2, w//2 - 26, "downloading planet data...")
    stdscr.refresh()

    ## jpl ephemeris - https://ssd.jpl.nasa.gov/ephem.html
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

    ## star data from hipparicos - https://www.cosmos.esa.int/web/hipparcos/
    stdscr.clear()
    stdscr.addstr(h//2, w//2 - 24, "downloading star data...")
    stdscr.refresh()
    with load.open(hipparcos.URL) as f:
        df = hipparcos.load_dataframe(f)
    bright_stars = df[df['magnitude'] <= 3.5]
    stars = Star.from_dataframe(bright_stars) # cast into skyfield object

    ### main drawing loop
    while True: 
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        t = ts.now()
        center_position = observer.at(t).from_altaz(alt_degrees=alt, az_degrees=azimuth)
        projection = build_stereographic_projection(center_position)

        ## draw stars
        astrometric = observer.at(t).observe(stars)
        x_stars, y_stars = projection(astrometric)
        mags = bright_stars['magnitude'].values
        for i in range(len(x_stars)):
            screen_x = (x_stars[i] / (fov/2) + 1) * (w / 2)
            screen_y = (-y_stars[i] / (fov/2) + 1) * (h / 2)
            if 0 <= screen_x < w and 0 <= screen_y < h:
                mag_index = min(int(mags[i]), len(scale)-1)
                stdscr.addch(int(screen_y), int(screen_x), scale[mag_index])
        
        ## draw bodies
        for name, body in bodies.items():
            astrometric = observer.at(t).observe(body)
            x_body, y_body = projection(astrometric)
            screen_x = (x_body / (fov/2) + 1) * (w / 2)
            screen_y = (-y_body / (fov/2) + 1) * (h / 2)
            if 0 <= screen_x < w and 0 <= screen_y < h:
                if fov == 1.0: # show full name
                    stdscr.addstr(int(screen_y), int(screen_x), name[0:3], curses.A_BOLD)
                else:
                    stdscr.addch(int(screen_y), int(screen_x), name[0], curses.A_BOLD)

        ### controls
        stdscr.addstr(0, 0, f"Az: {azimuth:.0f} Alt: {alt:.0f} Zoom: {fov:.1f} | arrows to move, w to zoom, s to unzoom, q to quit")
        key = stdscr.getch()
        
        # input
        if key == ord('q'): break
        elif key == curses.KEY_LEFT: azimuth = (azimuth - 5) % 360
        elif key == curses.KEY_RIGHT: azimuth = (azimuth + 5) % 360
        elif key == curses.KEY_UP: alt = min(90, alt + 5)
        elif key == curses.KEY_DOWN: alt = max(-90, alt - 5)
        elif key == ord('w'): fov = max(0.1, fov - 1.0)
        elif key == ord('s'): fov += 1.0

if __name__ == "__main__":
    curses.wrapper(main)