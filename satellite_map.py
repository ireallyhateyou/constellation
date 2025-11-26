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
   :::::::::::::::: :     ':::::::::   ' ,:::::::::: : :.:'::::::::::
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
    return int(x), int(y)

def display_map(stdscr, objects, ts):
    # force into lsit
    if not isinstance(objects, (list, tuple)):
        objects = [objects]

    stdscr.nodelay(1)

    # colors
    try:
        curses.init_pair(10, curses.COLOR_RED, curses.COLOR_BLACK)
        RED_BOLD = curses.color_pair(10) | curses.A_BOLD
    except:
        RED_BOLD = curses.A_BOLD | curses.A_REVERSE

    # load map text
    map_lines = [line for line in RAW_MAP.split("\n") if line]
    map_height = len(map_lines)
    map_width = len(map_lines[0]) if map_height > 0 else 0

    start_y = 1
    start_x = 1

    timestamp = 0
    marker_positions = []

    while True:
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
                stdscr.addstr(start_y + i, start_x, line)
            except curses.error:
                pass

        # draw each marker
        for lat, lon, name in marker_positions:
            px, py = project_mercator(lat, lon, map_width, map_height)
            screen_x = start_x + px
            screen_y = start_y + py

            try:
                stdscr.addch(screen_y, screen_x, 'X', RED_BOLD)
            except curses.error:
                pass

        # footer
        footer_y = start_y + map_height + 2
        stdscr.addstr(footer_y, start_x, "--- LIVE LOCATION ---")

        if not marker_positions:
            stdscr.addstr(footer_y + 1, start_x, "no data available")
        else:
            # list satellites
            for i, (lat, lon, name) in enumerate(marker_positions):
                line = f"{name}: LAT {lat:.2f}° | LON {lon:.2f}°"
                stdscr.addstr(footer_y + 1 + i, start_x, line)

        stdscr.addstr(footer_y + 1 + len(marker_positions) + 2, start_x, "press 'm' to return to telescope")
        stdscr.refresh()
        key = stdscr.getch()
        if key == ord('m') or key == ord('q'):
            break
