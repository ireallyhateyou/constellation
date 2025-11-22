"""
cosmodroma
"""

import curses
import time
import numpy as np
from skyfield import almanac
from skyfield.api import Star, load, wgs84
from skyfield.data import hipparcos
from skyfield.projections import build_stereographic_projection

# internal modules
from renderer import s_addch, start_menu, draw_circle
from data_loader import load_data

def normalize_angle(degrees):
    # force angles into [-180, 180]
    return (degrees + 180) % 360 - 180

def main(stdscr):
    # configuration for ASCII art and camera
    h = 24
    w = 80
    azimuth = 180.0 # all in degrees
    alt = 30.0 
    fov = 10.0 
    scale = " .:!+*$#@"
    preview_radius = 5
    deepzoom_fov = 0.01 # fov required for focus
    auto_rotate = True
    focused_body = "Moon" # body we focus on

    # colours
    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)

    # run start menu
    if not start_menu(stdscr):
        return

    # terminal stuff
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.timeout(30)
    sh, sw = stdscr.getmaxyx() # fetch terminal size
    h = sh 
    w = sw 
    stdscr.addstr(h//2, w//2 - 29, "downloading Ephemeris data...", curses.A_BLINK)
    stdscr.refresh()

    # load data
    ts, planets, observer, bodies, stars = load_data(stdscr, h, w)

    # focus on the moon by default
    t_init = ts.now()
    moon_init_obs = observer.at(t_init).observe(bodies["Moon"])
    moon_az, moon_alt, _ = moon_init_obs.apparent().altaz()
    azimuth = moon_az.degrees
    alt = max(-90, min(90, moon_alt.degrees))

    drawn_labels = {} # drawn labels
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
            raw_alt = center_alt.degrees
            alt = max(-90.0, min(90.0, raw_alt))
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
                # coordinates relative to the screen
                sx = (x_stars[i] / (fov/2) + 1) * (w / 2)
                sy = (-y_stars[i] / (fov/2) + 1) * (h / 2)
                s_addch(stdscr, sy, sx, '.', curses.color_pair(2))

        ## draw celestial bodies
        body_data = {}
        drawn_labels = {} # reset
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
                body_data = { 'name': name, 'dist': dist, 'illum': illum_val, 'ra': ra, 'dec': dec }
            else:
                ## draw labels
                # add real estate, only one can occupy a pixel
                is_occupied = False
                check_range = 2
                for dy in range(-1, 2):
                    for dx in range(-check_range, check_range):
                        if (int(sy)+dy) in drawn_labels and (int(sx)+dx) in drawn_labels[int(sy)+dy]:
                            is_occupied = True
                if not is_occupied:
                    label = name[:3] if fov < 5.0 else name[0]
                    s_addch(stdscr, sy, sx, label[0], curses.A_BOLD | curses.color_pair(1))
                    # mark pixel as occupied
                    drawn_labels.setdefault(int(sy), set()).add(int(sx))

        ## draw focus panel
        if body_data:
            horizon_msg = " [BELOW HORIZON]" if alt < 0 else ""
            lines = [
                f"--- {body_data['name']}{horizon_msg} ---",
                f"Dist: {body_data['dist']:.5f} AU",
                f"Phase: {body_data['illum']*100:.1f}%",
                f"RA: {body_data['ra'].hours:.2f}h",
                f"Dec: {body_data['dec'].degrees:.2f}"
            ]
            for i, line in enumerate(lines):
                if 2+i < h:
                    try: stdscr.addstr(i+2, w - 35, line, curses.color_pair(1))
                    except: pass

        ### controls
        mode = " [LOCKED]" if is_locked else (" [AUTO]" if auto_rotate else "")
        status = f"Az:{azimuth:.1f} Alt:{alt:.1f} Zoom:{fov:.3f}{mode} | 'r' rotate, 'w/s' zoom, 'q' quit"
        try: stdscr.addstr(0, 0, status[:w-1], curses.A_REVERSE)
        except: pass

        ## input
        key = stdscr.getch()
        if key == ord('q'): break
        if key == ord('r'): auto_rotate = not auto_rotate
        if key == curses.KEY_LEFT: 
            auto_rotate = False
            azimuth -= 2
        if key == curses.KEY_RIGHT: 
            auto_rotate = False
            azimuth += 2
        if key == curses.KEY_UP: 
            auto_rotate = False
            alt = min(90, alt + 2)
        if key == curses.KEY_DOWN: 
            auto_rotate = False
            alt = max(-90, alt - 2)
        if key == ord('w'): fov = max(0.001, fov * 0.9)
        if key == ord('s'): fov = min(120, fov * 1.1)
        azimuth %= 360 # make azimuth roll back
        time.sleep(0.05) # 20 FPS

if __name__ == "__main__":
    curses.wrapper(main)