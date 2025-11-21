"""
cosmodroma
"""

import curses
import math
import time
from skyfield.api import Star, load, wgs84
from skyfield.data import hipparcos
from skyfield.projections import build_stereographic_projection

def draw_circle(stdscr, y, x, radius, charmap):
    center_y = int(y)
    center_x = int(x)
    h, w = stdscr.getmaxyx()
    for dy in range(-radius, radius + 1):
        for dx in range(-radius * 2, radius * 2 + 1): # x2 for terminal aspect ratio
            distance = math.sqrt(dy*dy + (dx/2)*(dx/2)) # dx/2 for ratio correction
            normalized_dist = distance / radius
            # shade indices
            char_index = int(normalized_dist * (len(charmap) - 1))
            char_index = min(char_index, len(charmap) - 1)
            if center_y + dy < 0 or center_y + dy >= h or center_x + dx < 0 or center_x + dx >= w:
                continue # dont draw outside bounds
            # shading
            shade_char = charmap[len(charmap) - 1 - char_index]
            stdscr.addch(center_y + dy, center_x + dx, shade_char)

def main(stdscr):
    # configuration for ASCII art and camera
    h = 24
    w = 80
    azimuth = 180.0 # all in degrees
    alt = 30.0 
    fov = 10.0 
    scale = " .,:;+*#@"
    preview_radius = 5
    deepzoom_fov = 0.01 # fov required for focus

    # configuration for spaceslop
    lat = 40.7128 # this is NYC btw
    long = -74.0060
    focused_body = "Moon" # body we focus on

    # terminal stuff
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.timeout(50)
    sh, sw = stdscr.getmaxyx() # fetch terminal size
    # colours
    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    h = sh 
    w = sw 
    stdscr.addstr(h//2, w//2 - 26, "downloading planet data...")
    stdscr.refresh()

    ## jpl ephemeris - https://ssd.jpl.nasa.gov/ephem.html
    ts = load.timescale()
    planets = load("de421.bsp")
    earth = planets["earth"]
    observer = earth + wgs84.latlon(lat, long)
    bodies = { # celestial bodies that we will track
        "Mars": planets["mars"],
        "Venus": planets["venus"],
        "Jup": planets["jupiter barycenter"],
        "Sat": planets["saturn barycenter"],
        "Moon": planets["moon"]
    }

    ## star data from hipparicos - https://www.cosmos.esa.int/web/hipparcos/
    stdscr.clear()
    stdscr.addstr(h//2, w//2 - 24, "downloading star data...")
    stdscr.refresh()
    with load.open(hipparcos.URL) as f:
        df = hipparcos.load_dataframe(f)
    bright_stars = df[df["magnitude"] <= 3.5]
    stars = Star.from_dataframe(bright_stars) # cast into skyfield object

    ### main drawing loop
    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        t = ts.now() # real time!!!!
        center_position = observer.at(t).from_altaz(alt_degrees=alt, az_degrees=azimuth)
        projection = build_stereographic_projection(center_position)

        if fov <= deepzoom_fov and focused_body in bodies:
            ## update camera on our focused body if fov is locked in
            center_obj = observer.at(t).observe(bodies[focused_body])
            center_az, center_alt, _ = center_obj.apparent().altaz()            
            azimuth = center_az.degrees
            alt = center_alt.degrees
        center_position = observer.at(t).from_altaz(alt_degrees=alt, az_degrees=azimuth)
        projection = build_stereographic_projection(center_position)

        ## draw stars... only when we aren"t zooming
        if fov > deepzoom_fov * 2:
            astrometric = observer.at(t).observe(stars)
            x_stars, y_stars = projection(astrometric)
            mags = bright_stars["magnitude"].values
            for i in range(len(x_stars)):
                x_dist_au = x_stars[i]
                y_dist_au = y_stars[i]
                if x_dist_au**2 + y_dist_au**2 > (fov/2 * 2)**2: # prevent co-ords from blowing up
                    continue
                screen_x = (x_stars[i] / (fov/2) + 1) * (w / 2)
                screen_y = (-y_stars[i] / (fov/2) + 1) * (h / 2)
                if not math.isfinite(screen_x) or not math.isfinite(screen_y): # bro :sob:
                    continue
                if 0 <= screen_x < w and 0 <= screen_y < h: # force it to fit the aspect ratio
                    mag_value = mags[i] # a larger index for larger magnitude (dimmer stars)
                    mag_index = int(max(0, (3.5 - mag_value) * 9 / 3.5)) # scale from 0 to 9
                    mag_index = min(mag_index, len(scale)-1)
                    safe_y = max(0, min(h - 1, int(screen_y)))
                    safe_x = max(0, min(w - 1, int(screen_x)))
                    if safe_x < w-1 and safe_y < h-1:
                        stdscr.addch(safe_y, safe_x, scale[mag_index])

        ## draw celestial bodies
        body_data = {}
        for name, body in bodies.items():
            observation = observer.at(t).observe(body)
            astrometric = observation.apparent()
            x_body, y_body = projection(astrometric)
            screen_x = (x_body / (fov/2) + 1) * (w / 2)
            screen_y = (-y_body / (fov/2) + 1) * (h / 2)
            if name == focused_body and fov <= deepzoom_fov:
                # Draw the planet preview circle
                if 0 <= screen_x < w and 0 <= screen_y < h:
                    draw_circle(stdscr, screen_y, screen_x, preview_radius, scale)
                # Calculate details for the panel
                distance_au = observation.distance().au
                mag_val = None # figure a way out to do this
                ra, dec, _ = astrometric.radec()
                body_data = { 'name': name, 'dist': distance_au,
                             'mag': mag_val, 'ra': ra, 'dec': dec }
            elif 0 <= screen_x < w and 0 <= screen_y < h:
                if fov <= 1.0: # show 3 letters
                    sy = min(h-2, int(screen_y))
                    sx = min(w-4, int(screen_x))  # printing 3 chars -> avoid last 3 columns
                    stdscr.addstr(sy, sx, name[0:3], curses.A_BOLD)
                else: # show 1 letter
                    sy = min(h-2, int(screen_y))
                    sx = min(w-2, int(screen_x))
                    stdscr.addch(sy, sx, name[0], curses.A_BOLD)

        ## draw focus panel when you zoom in
        if fov <= deepzoom_fov and body_data:  
            panel_lines = [
                f"--- {body_data["name"]} ---",
                f" Distance: {body_data["dist"]:.2f} AU",
                f" RA: {body_data["ra"].hours:6.2f}h",
                f" Mag: {body_data["mag"]:.2f}" if body_data["mag"] is not None else " Mag: N/A",
                f" Dec: {body_data["dec"].degrees:6.2f}\u00b0" # degree symbol
            ]

            # print it, make sure it fits
            start_col = w - 30 
            start_row = 1
            for i, line in enumerate(panel_lines):
                if start_col >= 0 and start_row + i < h:
                    stdscr.addstr(start_row + i, start_col, line)

        ### controls
        fov_display = f"{fov:.3f}" if fov < 0.1 else f"{fov:.1f}"
        stdscr.addstr(0, 0, f"Az: {azimuth:.0f} Alt: {alt:.0f} Zoom: {fov_display} | arrows, w/s for zoom, q to quit")
        key = stdscr.getch()

        ## input
        if key == ord("q"): break
        elif key == curses.KEY_LEFT: azimuth = (azimuth - 5)
        elif key == curses.KEY_RIGHT: azimuth = (azimuth + 5)
        elif key == curses.KEY_UP: alt = min(90, alt + 5)
        elif key == curses.KEY_DOWN: alt = max(-90, alt - 5)
        elif key == ord("w"): 
            zoom_step = 0.001 if fov <= 0.1 else 1.0 
            fov = max(0.001, fov - zoom_step)
        elif key == ord("s"): 
            zoom_step = 0.001 if fov < deepzoom_fov * 10 else 1.0 
            fov = min(90.0, fov + zoom_step)
        azimuth = azimuth % 360

if __name__ == "__main__":
    curses.wrapper(main)