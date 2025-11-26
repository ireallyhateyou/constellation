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

def display_map(stdscr, object, ts):
    stdscr.nodelay(1)
    # color for the marker
    try:
        curses.init_pair(10, curses.COLOR_RED, curses.COLOR_BLACK) 
        RED_BOLD = curses.color_pair(10) | curses.A_BOLD
    except:
        RED_BOLD = curses.A_BOLD | curses.A_REVERSE

    # map variables
    map_lines = [line for line in RAW_MAP.split('\n') if line]
    map_height = len(map_lines)
    map_width = len(map_lines[0]) if map_height > 0 else 0
    start_y = 1
    start_x = 1
    current_lat, current_lon, timestamp = None, None, 0
    
    while True:
        timestamp = ts.now()
        geocentric = object.at(timestamp)
        subpoint = wgs84.subpoint(geocentric)
        current_lat = subpoint.latitude.degrees
        current_lon = subpoint.longitude.degrees

        stdscr.clear()
        for i, line in enumerate(map_lines):
            try:
                stdscr.addstr(start_y + i, start_x, line)
            except curses.error:
                pass 

        if current_lat is not None:
            # project and draw marker
            px, py = project_mercator(current_lat, current_lon, map_width, map_height)
            screen_x = start_x + px
            screen_y = start_y + py
            try:
                stdscr.addch(screen_y, screen_x, 'X', RED_BOLD)
            except curses.error:
                pass

        footer_y = start_y + map_height + 2
        
        info = "--- LIVE POSITION ---"
        stdscr.addstr(footer_y, start_x, info)
        
        if current_lat is not None:
            pos_info = f"LAT: {current_lat:.2f}° | LON: {current_lon:.2f}° (TS: {timestamp})"
            stdscr.addstr(footer_y + 1, start_x, pos_info)
        else:
            stdscr.addstr(footer_y + 1, start_x, "waiting for ISS data...")
            
        stdscr.addstr(footer_y + 3, start_x, "Press 'm' to return to telescope")
        stdscr.refresh()
        key = stdscr.getch()
        if key == ord('m') or key == ord('q'):
            break
        time.sleep(5) 
