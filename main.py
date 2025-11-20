"""
constellation viewer
"""

import curses
import math
import time
from skyfield.api import Star, load, wgs84
from skyfield.data import hipparcos
from skyfield.projections import build_stereographic_projection

def draw_circle(stdscr, center_y, center_x, radius, charmap):
    h, w = stdscr.getmaxyx()
    for y in range(h):
        for x in range(w):
            dy = y - center_y
            dx = x - center_x
            distance = math.sqrt(dx*dx + dy*dy)
            if distance <= radius:
                shade_index = int((distance / radius) * (len(charmap) - 1))
                stdscr.addch(y, x, charmap[shade_index])

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
    focused_body = 'Moon' # body we focus on

    # terminal stuff
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

        if fov <= 0.1 and focused_body in bodies:
            ## update camera on our focused body if fov is locked in
            center_obj = observer.at(t).observe(bodies[focused_body])
            center_az, center_alt, _ = center_obj.apparent().altaz()            
            azimuth = center_az.degrees
            alt = center_alt.degrees
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
                mag_value = mags[i] # a larger index for larger magnitude (dimmer stars)
                mag_index = int(max(0, (3.5 - mag_value) * 9 / 3.5)) # scale from 0 to 9
                mag_index = min(mag_index, len(scale)-1)
                stdscr.addch(int(screen_y), int(screen_x), scale[mag_index])

        ## draw celestial bodies
        body_data = {}
        for name, body in bodies.items():
            astrometric = observer.at(t).observe(body)
            x_body, y_body = projection(astrometric)
            screen_x = (x_body / (fov/2) + 1) * (w / 2)
            screen_y = (-y_body / (fov/2) + 1) * (h / 2)
            if name == focused_body and fov <= 0.1:
                distance_au = astrometric.distance().au
                mag_val = None # TODO: get v-band magnitude myself
                ra, dec, _ = astrometric.radec()
                body_data = { 'name': name, 'dist': distance_au, 
                             'mag': mag_val, 'ra': ra, 'dec': dec }
            if 0 <= screen_x < w and 0 <= screen_y < h:
                if fov <= 1.0: # show 
                    stdscr.addstr(int(screen_y), int(screen_x), name[0:3], curses.A_BOLD)
                else:
                    stdscr.addch(int(screen_y), int(screen_x), name[0], curses.A_BOLD)

        ## draw focus panel when you zoom in
        if fov <= 0.1 and body_data:  
            panel_lines = [
                f"--- {body_data['name']} ---",
                f" Distance: {body_data['dist']:.2f} AU",
                #f" Mag: {body_data['mag']:.2f}" if body_data['mag'] is not None else " Mag: N/A",
                f" RA: {body_data['ra'].hours:6.2f}h",
                f" Dec: {body_data['dec'].degrees:6.2f}\u00b0" # degree symbol
            ]
            
            # print it, make sure it fits.
            start_col = w - 30 
            start_row = 1
            for i, line in enumerate(panel_lines):
                if start_col >= 0 and start_row + i < h:
                    stdscr.addstr(start_row + i, start_col, line)
                    
        ### controls
        stdscr.addstr(0, 0, f"Az: {azimuth:.0f} Alt: {alt:.0f} Zoom: {fov:.1f} | arrows to move, w to zoom, s to unzoom, q to quit")
        key = stdscr.getch()

        ## input
        if key == ord('q'): break
        elif key == curses.KEY_LEFT: azimuth = (azimuth - 5) % 360
        elif key == curses.KEY_RIGHT: azimuth = (azimuth + 5) % 360
        elif key == curses.KEY_UP: alt = min(90, alt + 5)
        elif key == curses.KEY_DOWN: alt = max(-90, alt - 5)
        elif key == ord('w'): fov = max(0.1, fov - 1.0)
        elif key == ord('s'): fov += 1.0

if __name__ == "__main__":
    curses.wrapper(main)