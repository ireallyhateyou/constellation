"""
cosmodroma
"""
import math
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
    focused_body = "Sun" # body we focus on
    pan_active = False
    pan_start_az = azimuth
    pan_start_alt = alt
    pan_target_az = azimuth
    pan_target_alt = alt
    pan_start_time = 0.0
    pan_duration = 0.35  # seconds to complete pan

    # colours
    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)

    # run start menu
    if not start_menu(stdscr):
        return

    # terminal stuff
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.keypad(True)
    stdscr.timeout(30)
    sh, sw = stdscr.getmaxyx() # fetch terminal size
    h = sh 
    w = sw 
    stdscr.addstr(h//2, w//2 - 29, "downloading Ephemeris data...", curses.A_BLINK)
    stdscr.refresh()

    # load data
    ts, planets, observer, bodies, stars = load_data(stdscr, h, w)

    # focus on the sun by default
    t_init = ts.now()
    if pan_active: # I forgot what this does
        elapsed = time.time() - pan_start_time
        frac = min(1.0, max(0.0, elapsed / pan_duration))
        d_az = normalize_angle(pan_target_az - pan_start_az)
        azimuth = (pan_start_az + d_az * frac) % 360
        alt = pan_start_alt + (pan_target_alt - pan_start_alt) * frac
        alt = max(-90.0, min(90.0, alt))
        if frac >= 1.0:
            pan_active = False
            pass

    sun_init_obs = observer.at(t_init).observe(bodies["Sun"])
    sun_az, sun_alt, _ = sun_init_obs.apparent().altaz()
    azimuth = sun_az.degrees
    alt = max(-90, min(90, sun_alt.degrees))

    drawn_labels = {} # drawn labels
    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        t = ts.now()
        is_locked = (fov <= deepzoom_fov and focused_body in bodies) # if locked in...
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
            # colors per planet
            color_attr = curses.color_pair(1)
            if name == "Mars": color_attr = curses.color_pair(3)
            elif name == "Sun": color_attr = curses.color_pair(4) | curses.A_BOLD 
            elif name == "Jupiter": color_attr = curses.color_pair(4) 
            elif name == "Venus": color_attr = curses.color_pair(5) 
            elif name == "Moon": color_attr = curses.color_pair(1)
            illum_val = 1.0
            if name == "Moon":
                # moon phase
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
                    s_addch(stdscr, sy, sx, label[0], curses.A_BOLD | color_attr)
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
        target_str = f" Target:{focused_body}" if not is_locked else ""
        status = f"Az:{azimuth:.1f} Alt:{alt:.1f} Zoom:{fov:.3f}{target_str} | 'r' rotate, 'w/s' zoom, 'e' target, 'q' quit"
        try: stdscr.addstr(0, 0, status[:w-1], curses.A_REVERSE)
        except: pass

        ## input
        key = stdscr.getch()
        if key == ord('q'): break
        if key == ord('e'):
            stdscr.nodelay(0)
            curses.echo()
            prompt = "Enter target name (e.g., Moon, Mars, Sun) and press ENTER: "
            stdscr.addstr(h-2, 0, prompt, curses.A_REVERSE)
            try:
                input_bytes = stdscr.getstr(h-2, len(prompt), 30) # get input
                target_name = input_bytes.decode('utf-8').strip().title()
            except:
                target_name = ""
            if target_name in bodies:
                focused_body = target_name
            curses.noecho()
            stdscr.addstr(h-2, 0, ' ' * w)
            stdscr.nodelay(1)
        if key == curses.KEY_LEFT: azimuth -= 2
        if key == curses.KEY_RIGHT: azimuth += 2
        if key == curses.KEY_UP: alt = min(90, alt + 2)
        if key == curses.KEY_DOWN: alt = max(-90, alt - 2)
        if key == ord('w'): fov = max(0.001, fov * 0.9)
        if key == ord('s'): fov = min(120, fov * 1.1)
        azimuth %= 360 # make azimuth roll back

if __name__ == "__main__":
    curses.wrapper(main)