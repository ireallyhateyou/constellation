import curses
import math
import time
import requests
from skyfield.api import wgs84

RAW_MAP = """
   :::::::::::''  ''::'      '::::::  `:::::::::::::'.:::::::::::::::
   :::::::::' :. :  :         ::::::  :::::::::::.:::':::::::::::::::
   ::::::::::  :   :::.       :::::::::::::..::::'     :::: : :::::::
   ::::::::    :':  "::'     '"::::::::::::: :'           '' ':::::::
   :'        : '   :  ::    .::::::::'    '                    .:
   :               :  .:: .::. ::::'                          :::
   :. .,.        :::  ':::::::::::.: '                     .:...::::
   :::::::.      '     .::::::: '''                         :: :::::.
   ::::::::            ':::::::::  '',            '    '   .:::::::::
   ::::::::.        :::::::::::: '':,:   '    :         ''' :::::::::
   ::::::::::      ::::::::::::'                        :::::::::::::
   : .::::::::.   .:''::::::::    '        ::   :   '::.::::::::::::
   :::::::::::::::. '  '::::::.  '  '     :::::.:.:.:.:.:::::::::::::
   :::::::::::::::: :     ':::::::::   . :'::::::::::::::' '::::::::::
   ::::::::::::::::: '     :::::::::   . :'::::::::::::::' ':::::::::
   ::::::::::::::::::''   :::::::::: :' : ,:::::::::::'      ':::::::
   :::::::::::::::::'   .::::::::::::  ::::::::::::::::       :::::::
   :::::::::::::::::. .::::::::::::::::::::::::::::::::::::.'::::::::
   :::::::::::::::::' :::::::::::::::::::::::::::::::::::::::::::::::
   ::::::::::::::::::.:::::::::::::::::::::::::::::::::::::::::::::::
"""

# project lat long coords to x y coordinates
def project_mercator(lat, lon, map_width, map_height):
    x = (lon + 180) * (map_width / 360.0)
    #https://en.wikipedia.org/wiki/Transverse_Mercator_projection
    lat = max(min(lat, 85), -85) # clamp to 85 deg
    lat_rad = math.radians(lat)
    merc_y = math.log(math.tan((math.pi / 4) + (lat_rad / 2)))
    max_merc = 3.13 # max value for 85 degrees

    # normalize and invert Y
    y_norm = (merc_y + max_merc) / (2 * max_merc)
    y_norm = 1.0 - y_norm    
    y = y_norm * map_height
    
    # Clamp to map dimensions to prevent "out of bounds"
    x = max(0, min(int(x), map_width - 1))
    y = max(0, min(int(y), map_height - 1))
    
    return x, y

def display_map(stdscr, objects, ts):
    # force into list
    if not isinstance(objects, (list, tuple)):
        objects = [objects]

    stdscr.nodelay(1)
    
    # colors
    try:
        curses.init_pair(10, curses.COLOR_RED, curses.COLOR_BLACK)
        RED_BOLD = curses.color_pair(10) | curses.A_BOLD
        curses.init_pair(11, curses.COLOR_WHITE, curses.COLOR_BLACK) # fallback
    except:
        RED_BOLD = curses.A_BOLD | curses.A_REVERSE

    # load map text and strip tariling spaces
    map_lines = [line.lstrip() for line in RAW_MAP.split("\n") if line.strip()]
    map_height = len(map_lines)
    map_width = max(len(line) for line in map_lines) if map_height > 0 else 0

    timestamp = 0
    marker_positions = []

    while True:
        sh, sw = stdscr.getmaxyx()
        
        # center midlde map
        start_y = max(1, (sh - map_height) // 2)
        start_x = max(0, (sw - map_width) // 2)

        timestamp = ts.now()
        marker_positions.clear()

        # figure out locations for all satellites
        for obj in objects:
            geocentric = obj.at(timestamp)
            subpoint = wgs84.subpoint(geocentric)

            lat = subpoint.latitude.degrees
            lon = subpoint.longitude.degrees

            name = getattr(obj, "name", "SAT")
            marker_positions.append((lat, lon, name))

        stdscr.clear()

        # draw world map
        for i, line in enumerate(map_lines):
            try:
                if 0 <= start_y + i < sh:
                    stdscr.addstr(start_y + i, start_x, line)
            except curses.error:
                pass

        # draw each marker
        is_focused = (len(objects) == 1)
        
        for lat, lon, name in marker_positions:
            px, py = project_mercator(lat, lon, map_width, map_height)
            screen_x = start_x + px
            screen_y = start_y + py
            
            if is_focused:
                marker_char = '●' # dot for focused
            else:
                marker_char = name[0].upper() if name else '?' # name initial

            try:
                # no oob printin
                if 0 <= screen_y < sh and 0 <= screen_x < sw - 1:
                    stdscr.addch(screen_y, screen_x, marker_char, RED_BOLD)
            except curses.error:
                pass

        # control text
        status_text = "'m' or 'q' to return "
        try:
            stdscr.addstr(0, 0, status_text, curses.A_REVERSE)
        except curses.error:
            pass

        # data
        space_below = sh - (start_y + map_height)
        info_y = start_y + map_height + 2
        info_x = start_x
        
        # change location of its full
        if space_below < 5: 
            space_right = sw - (start_x + map_width)
            if space_right > 25: # width
                info_y = start_y
                info_x = start_x + map_width + 3 # 3 spaces gap

        try:
            # dont do off screen
            if 0 <= info_y < sh:
                stdscr.addstr(info_y, info_x, "--- LIVE LOCATION ---")
             
            if not marker_positions:
                if 0 <= info_y + 1 < sh:
                    stdscr.addstr(info_y + 1, info_x, "no data available")
            else:
                for i, (lat, lon, name) in enumerate(marker_positions):
                    line = f"{name}: LAT {lat:.2f}° | LON {lon:.2f}°"
                    if 0 <= info_y + 1 + i < sh: 
                        stdscr.addstr(info_y + 1 + i, info_x, line)
        except curses.error:
            pass

        stdscr.refresh()
        key = stdscr.getch()
        if key == ord('m') or key == ord('q'):
            break