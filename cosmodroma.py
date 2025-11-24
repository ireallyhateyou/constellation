"""
cosmodroma
"""

import math
import curses
import time
import numpy as np
import datetime
from zoneinfo import ZoneInfo
from skyfield import almanac
from skyfield.api import Star, load, wgs84
from skyfield.data import hipparcos
from skyfield.projections import build_stereographic_projection
# internal modules
from renderer import s_addch, start_menu, draw_circle, draw_iss
from data_loader import load_data
from iss import iss_map

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
    deepzoom_fov = 0.041 # fov required for focus
    focused_body = "ISS" # body we focus on

    # colours
    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)

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
    ts, planets, observer, topos_observer, bodies, stars = load_data(stdscr, h, w)
    planets_list = list(bodies.keys())
    drawn_labels = {} 
    min_distance_sq = float('inf')
    closest_body_in_view = None
    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        t = ts.now()
        is_locked = (fov <= deepzoom_fov and focused_body in bodies) # if locked in...
        ## update camera on our focused body if fov is locked in
        if is_locked:
            body_to_focus = bodies[focused_body]
            if focused_body == "ISS":
                # EarthSatellite (TLEs)
                topocentric = (body_to_focus - topos_observer).at(t)
                center_az, center_alt, _ = topocentric.altaz()
                center_position = observer.at(t).from_altaz(alt_degrees=center_alt.degrees, az_degrees=center_az.degrees)
            else:
                # planets (JPL Ephemeris)
                target_body = observer.at(t).observe(body_to_focus)
                center_position = target_body.apparent()
                center_az, center_alt, _ = center_position.altaz()          
            azimuth = center_az.degrees
            raw_alt = center_alt.degrees
            alt = max(-90.0, min(90.0, raw_alt))
        else:
            # just move it yourself
            center_position = observer.at(t).from_altaz(alt_degrees=alt, az_degrees=azimuth)

        ## build the camera view from that center
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
            current_dist = None
            if name == "ISS":
                topocentric = (body - topos_observer).at(t)
                az_ang, alt_ang, current_dist = topocentric.altaz()
                astrometric = observer.at(t).from_altaz(alt_degrees=alt_ang.degrees, az_degrees=az_ang.degrees)
            else:
                # observation for planets
                observation = observer.at(t).observe(body)
                astrometric = observation.apparent()
                current_dist = observation.distance()  
            x_body, y_body = projection(astrometric)
            # coords relative to the screen
            sx = (x_body / (fov/2) + 1) * (w / 2)
            sy = (-y_body / (fov/2) + 1) * (h / 2)
            distance_sq = x_body**2 + y_body**2
            if distance_sq < min_distance_sq:
                min_distance_sq = distance_sq
                closest_body_in_view = name

            # colors per planet
            has_rings = (name in ["Saturn", "Uranus", "Neptune"]) # hehe
            color_attr = curses.color_pair(1)
            if name == "Mars": color_attr = curses.color_pair(3)
            elif name == "Sun": color_attr = curses.color_pair(4) | curses.A_BOLD 
            elif name == "Jupiter": color_attr = curses.color_pair(4) 
            elif name == "Venus": color_attr = curses.color_pair(5) 
            elif name == "Moon": color_attr = curses.color_pair(1)
            elif name == "Saturn": 
                color_attr = curses.color_pair(4) 
                ring_attr = curses.color_pair(6) | curses.A_BOLD # ring
            elif name == "Uranus":
                color_attr = curses.color_pair(2)
                ring_attr = curses.color_pair(1)
            elif name == "Neptune":
                color_attr = curses.color_pair(7)
                ring_attr = curses.color_pair(1)
            elif name == "ISS":
                color_attr = curses.color_pair(8) | curses.A_BOLD
            illum_val = 1.0
            if name == "Moon":
                # moon phase
                illum_val = almanac.fraction_illuminated(planets, 'moon', t)
 
            # draw focused body if in deep zoom
            if name == focused_body and fov <= deepzoom_fov:
                if name == "ISS":
                    draw_iss(stdscr, sy, sx, color_attr)
                else:
                    true_and_real_ring_attr = ring_attr if has_rings else None
                    draw_circle(stdscr, sy, sx, preview_radius, scale, float(illum_val), 
                                color_attr, has_rings, true_and_real_ring_attr)
                if focused_body == "ISS":
                    dist_str = f"{(current_dist.km):.1f} km"
                else:
                    dist_str = f"{(current_dist.au):.5f} AU"
                ra, dec, _ = astrometric.radec()
                body_data = { 'name': name, 'dist': dist_str, 'illum': illum_val, 'ra': ra, 'dec': dec }
            else:
                ## draw labels
                # add real estate, only one can occupy a pixel
                is_occupied = False
                check_range = 2
                for dy in range(-1, 2):
                    for dx in range(-check_range, check_range):
                        if (int(sy)+dy) in drawn_labels and (int(sx)+dx) in drawn_labels[int(sy)+dy]:
                            is_occupied = True
                 # don't show satelites since they dont exist in relation to the moon but rather the sun
                if not is_occupied and name != "ISS":
                    if fov > 5.0:
                        # planet marker
                        s_addch(stdscr, sy, sx, '●', curses.A_BOLD | color_attr)
                    else:
                        # zoomed shows name
                        if 0 <= sy < h and 0 <= sx < w - len(name):
                            try: stdscr.addstr(int(sy), int(sx), name, curses.A_BOLD | color_attr)
                            except: pass
                    # mark pixel as occupied
                    drawn_labels.setdefault(int(sy), set()).add(int(sx))

        ## draw focus panel
        if body_data:
            horizon_msg = " [BELOW HORIZON]" if alt < 0 else ""
            lines = [
                f"--- {body_data['name']}{horizon_msg} ---",
                f"Dist: {body_data['dist']}",
                *([f"Phase: {body_data['illum']*100:.1f}%"] if body_data['name'] == 'Moon' else []),
                f"RA: {body_data['ra'].hours:.2f}h",
                f"Dec: {body_data['dec'].degrees:.2f}"
            ]
            for i, line in enumerate(lines):
                if 2+i < h:
                    try: stdscr.addstr(i+2, w - 35, line, curses.color_pair(1))
                    except: pass

        ### status bar
        status = f"Az:{azimuth:.1f} Alt:{alt:.1f} Zoom:{fov:.3f} | 'w/s' zoom, 'e' target, 'q' quit"
        status_focus = f"'s' unzoom, 'left/right' showcase planets, 'e' change target" 
        if is_locked and focused_body == "ISS":
            status_focus = f"{status_focus}, 'm' map view"
        try: stdscr.addstr(0, 0, status_focus[:w-1] if is_locked else status[:w-1], curses.A_REVERSE)
        except: pass

        ### time
        nyc_tz = ZoneInfo("America/New_York")
        now = datetime.datetime.now(nyc_tz)
        time_str = f"New York, NY ; {now.strftime('%Hh%M')}"
        try: stdscr.addstr(h-1, w - len(time_str) - 1, time_str, curses.color_pair(1))
        except: pass

        ## input
        key = stdscr.getch()
        if key == ord('m') and is_locked and focused_body == "ISS":
            iss_map(stdscr)
            continue
        if key == ord('q'): break
        if key == ord('e'):
            # TODO: make a way that doesn't fkn restore to terminal ffs
            try:
                curses.nocbreak()
                stdscr.keypad(False)
                curses.echo()
                curses.curs_set(1)
                curses.endwin()
                try:
                    # WHY
                    target_name = input("Enter target name (Moon, Mars, ISS, Sun): ").strip().title()
                    if target_name.upper() == "ISS": target_name = "ISS"
                except Exception:
                    target_name = ""
            finally:
                stdscr = curses.initscr() # new instance
                curses.noecho()
                curses.cbreak()
                stdscr.keypad(True)
                try:
                    curses.curs_set(0)
                except:
                    pass
                stdscr.nodelay(1)
                stdscr.clear()
                stdscr.refresh()
                try:
                    sh, sw = stdscr.getmaxyx()
                    h, w = sh, sw
                except:
                    pass
            if target_name in bodies:
                is_locked = True
                focused_body = target_name
                fov = deepzoom_fov # lol
            continue
        if is_locked:
            if key == curses.KEY_RIGHT:
                current_idx = planets_list.index(focused_body)
                focused_body = planets_list[(current_idx + 1) % len(planets_list)]
            if key == curses.KEY_LEFT:
                current_idx = planets_list.index(focused_body)
                focused_body = planets_list[(current_idx - 1) % len(planets_list)]
        else:
            if key == curses.KEY_LEFT: azimuth -= 2
            if key == curses.KEY_RIGHT: azimuth += 2
            if key == curses.KEY_UP: alt = min(90, alt + 2)
            if key == curses.KEY_DOWN: alt = max(-90, alt - 2)
        if key == ord('w'): 
            new_fov = max(0.001, fov * 0.9)
            if not is_locked and fov > deepzoom_fov and new_fov <= deepzoom_fov:
                if closest_body_in_view:
                    focused_body = closest_body_in_view
                    new_fov = deepzoom_fov 
            fov = new_fov
        if key == ord('s'): fov = min(120, fov * 1.1)
        azimuth %= 360 # make azimuth roll back

if __name__ == "__main__":
    curses.wrapper(main)