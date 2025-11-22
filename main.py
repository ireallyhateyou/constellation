"""
cosmodroma
"""

import curses
import math
import time
from skyfield import almanac
from skyfield.api import Star, load, wgs84
from skyfield.data import hipparcos
from skyfield.projections import build_stereographic_projection
import numpy as np

def s_addch(stdscr, y, x, char, attr=0): # safe character drawing
    h, w = stdscr.getmaxyx()
    if 0 <= y < h and 0 <= x < w: # only if it is within bounds.
        try:
            stdscr.addch(int(y), int(x), char, attr)
        except:
            pass

def normalize_angle(degrees):
    # force angles into [-180, 180]
    return (degrees + 180) % 360 - 180

def draw_circle(stdscr, y, x, radius, charmap, illumination=1.0):
    center_y = int(y)
    center_x = int(x)
    
    # light direction based on phase
    angle = (1.0 - illumination) * math.pi 
    lx = math.sin(angle)
    lz = math.cos(angle)

    # white (bold)
    attr = curses.color_pair(1) | curses.A_BOLD

    for dy in range(-radius, radius + 1):
        for dx in range(-radius * 2, radius * 2 + 1):
            # correct aspect ratio
            dist_sq = (dy * dy) + (dx / 2.0) ** 2
            dist = math.sqrt(dist_sq)
            if dist > radius: continue 

            # 3d sphere
            px = (dx / 2.0) / radius
            py = dy / radius
            pz_sq = 1.0 - px*px - py*py
            
            if pz_sq < 0: continue
            pz = math.sqrt(pz_sq)

            # lambert shading - https://lavalle.pl/vr/node197.html
            dot = px * lx + pz * lz
            brightness = max(0, dot)
            
            if brightness > 0.05:
                # lit side
                idx = int(brightness * (len(charmap) - 1))
                char = charmap[idx]
                s_addch(stdscr, center_y + dy, center_x + dx, char, attr)
            else:
                # dark hemisphere
                # make a grid pattern
                is_grid = (center_x + dx) % 2 == 0 and (center_y + dy) % 2 == 0
                char = '.' if is_grid else ' ' 
                if dist > radius - 1: char = ':' 
                s_addch(stdscr, center_y + dy, center_x + dx, char, curses.color_pair(2) | curses.A_BOLD)

def main(stdscr):
    # configuration for ASCII art and camera
    h = 24
    w = 80
    azimuth = 180.0 # all in degrees
    alt = 30.0 
    fov = 10.0 
    scale = " .:!+*$#@"
    preview_radius = 8
    deepzoom_fov = 0.01 # fov required for focus
    auto_rotate = True

    # configuration for spaceslop
    lat = 40.7128 # this is NYC btw
    long = -74.0060
    focused_body = "Moon" # body we focus on

    # terminal stuff
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.timeout(30)

    # colours
    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)

    sh, sw = stdscr.getmaxyx() # fetch terminal size
    h = sh 
    w = sw 
    stdscr.addstr(h//2, w//2 - 26, "downloading planet data...")
    stdscr.refresh()

    ### load data
    ## jpl ephemeris
    ts = load.timescale()
    planets = load("de421.bsp")
    earth = planets["earth"]
    observer = earth + wgs84.latlon(lat, long)
    bodies = { "Mars": planets["mars"], "Venus": planets["venus"], 
               "Jupiter": planets["jupiter barycenter"], "Moon": planets["moon"] }

    ## star data
    stdscr.clear()
    stdscr.addstr(h//2, w//2 - 24, "downloading star data...")
    stdscr.refresh()
    with load.open(hipparcos.URL) as f:
        df = hipparcos.load_dataframe(f)
    bright_stars = df[df["magnitude"] <= 3.5]
    stars = Star.from_dataframe(bright_stars) 

    # focus on the moon by default
    t_init = ts.now()
    moon_init_obs = observer.at(t_init).observe(bodies["Moon"])
    moon_az, moon_alt, _ = moon_init_obs.apparent().altaz()
    azimuth = moon_az.degrees
    alt = moon_alt.degrees

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        t = ts.now()

        # auto rotate
        is_locked = (fov <= deepzoom_fov and focused_body in bodies)
        if auto_rotate and not is_locked:
            azimuth = (azimuth + 0.1) % 360 

        ## update camera on our focused body if fov is locked in
        if is_locked:
            target_body = observer.at(t).observe(bodies[focused_body])
            center_position = target_body.apparent()
            # update ui stuff
            center_az, center_alt, _ = center_position.altaz()            
            azimuth = center_az.degrees
            alt = center_alt.degrees
        else:
            # just move it yourself
            center_position = observer.at(t).from_altaz(alt_degrees=alt, az_degrees=azimuth)

        # build the camera view from that center
        projection = build_stereographic_projection(center_position)

        ## draw stars
        if fov > deepzoom_fov * 2:
            astrometric = observer.at(t).observe(stars)
            x_stars, y_stars = projection(astrometric)
            limit = (fov/2 * 2)**2
            for i in range(len(x_stars)):
                if x_stars[i]**2 + y_stars[i]**2 > limit: continue
                sx = (x_stars[i] / (fov/2) + 1) * (w / 2)
                sy = (-y_stars[i] / (fov/2) + 1) * (h / 2)
                s_addch(stdscr, sy, sx, '.', curses.color_pair(2))

        ## draw celestial bodies
        body_data = {}
        
        for name, body in bodies.items():
            observation = observer.at(t).observe(body)
            astrometric = observation.apparent()
            x_body, y_body = projection(astrometric)
            
            # coords relative to the screen
            sx = (x_body / (fov/2) + 1) * (w / 2)
            sy = (-y_body / (fov/2) + 1) * (h / 2)
            
            illum_val = 1.0
            if name == "Moon":
                # TODO: this actually doesn't give proper data, figure this out.
                illum_val = almanac.fraction_illuminated(planets, 'moon', t)

            if name == focused_body and fov <= deepzoom_fov:
                draw_circle(stdscr, sy, sx, preview_radius, scale, float(illum_val))
                dist = observation.distance().au
                ra, dec, _ = astrometric.radec()
                body_data = { 'name': name, 'dist': dist, 'illum': illum_val, 'ra': ra, 'dec': dec, 'sx': sx }
            else:
                # draw label
                label = name[:3] if fov < 5.0 else name[0]
                s_addch(stdscr, sy, sx, label[0], curses.A_BOLD | curses.color_pair(1))

        ## draw focus panel
        if body_data:
            horizon_msg = " [BELOW HORIZON]" if alt < 0 else ""
            lines = [
                f"--- {body_data['name']}{horizon_msg} ---",
                f"Dist: {body_data['dist']:.5f} AU",
                f"Phase: {body_data['illum']*100:.1f}%",
                f"Screen X: {int(body_data['sx'])} (Center is {w//2})", 
                f"RA: {body_data['ra'].hours:.2f}h",
                f"Dec: {body_data['dec'].degrees:.2f}"
            ]
            for i, line in enumerate(lines):
                if 2+i < h:
                    try: stdscr.addstr(i+2, w - 35, line, curses.color_pair(1))
                    except: pass

        ### controls
        norm_alt = normalize_angle(alt)
        norm_az = normalize_angle(azimuth)
        mode = " [LOCKED]" if is_locked else (" [AUTO]" if auto_rotate else "")
        status = f"Az:{norm_az:.1f} Alt:{norm_alt:.1f} Zoom:{fov:.3f}{mode} | 'r' rotate, 'w/s' zoom, 'q' quit"
        try: stdscr.addstr(0, 0, status[:w-1], curses.A_REVERSE)
        except: pass

        ## input
        key = stdscr.getch()
        if key == ord('q'): break
        if key == ord('r'): auto_rotate = not auto_rotate
        if key == curses.KEY_LEFT: azimuth -= 2
        if key == curses.KEY_RIGHT: azimuth += 2
        if key == curses.KEY_UP: alt = min(90, alt + 2)
        if key == curses.KEY_DOWN: alt = max(-90, alt - 2)
        if key == ord('w'): fov = max(0.001, fov * 0.9)
        if key == ord('s'): fov = min(120, fov * 1.1)
        azimuth %= 360 # make azimuth roll back

if __name__ == "__main__":
    curses.wrapper(main)