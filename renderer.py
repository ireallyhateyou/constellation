import curses
import math

iss_ascii = """
                             
   |#| |#|           |#| |#|
   |#| |#| -;__@__   |#| |#|
   |#| |#|  ___|___  |#| |#|
  =@@@@@@@=[_______]=@@@@@@@=
   |#| |#| !!  |  !! |#| |#|
   |#| |#| !!__|__!! |#| |#|
   |#| |#|     ;     |#| |#|
                             
"""

hubble_ascii = """

     ______________
   C(              |;
     |_____________| 
           !
           0
                         
"""

tiangong_ascii = """

          ##______##               
   |#|#|     |  |     |#|#|
   |#|#| ####|  |#### |#|#|
   |#|#| ____|  |____ |#|#|
     !==[____________]==!
   |#|#|       |      |#|#|
   |#|#|    ###!###   |#|#|
   |#|#|              |#|#|
                             
"""

LOCATIONS = {
    "New York, NY": {"lat": 40.7128, "lon": -74.0060, "tz": "America/New_York"},
    "London (Greenwich)": {"lat": 51.4934, "lon": 0.0098, "tz": "Europe/London"},
    "Tokyo, Japan": {"lat": 35.6762, "lon": 139.6503, "tz": "Asia/Tokyo"},
    "Mauna Kea (Hawai'i)": {"lat": 19.8207, "lon": -155.4681, "tz": "Pacific/Honolulu"},
    "Paranal, Chile": {"lat": -24.6275, "lon": -70.4044, "tz": "America/Santiago"},
    "Sutherland (SAAO)": {"lat": -32.3760, "lon": 20.8107, "tz": "Africa/Johannesburg"}
}

def s_addch(stdscr, y, x, char, attr=0): # safe character drawing
    h, w = stdscr.getmaxyx()
    if 0 <= y < h and 0 <= x < w: # only if it is within bounds.
        try:
            stdscr.addch(int(y), int(x), char, attr)
        except:
            pass

def draw_satellite(stdscr, name, y, x, color_attr):
    if name == "Tiangong":
        ascii_art = tiangong_ascii
    elif name == "Hubble":
        ascii_art = hubble_ascii
    else:
        ascii_art = iss_ascii

    lines = ascii_art.splitlines()
    h_ascii = len(lines)
    w_ascii = max(len(line) for line in lines)
    start_y = int(y - h_ascii / 2) 
    start_x = int(x - w_ascii / 2)
    
    for i, line in enumerate(lines):
        for j, char in enumerate(line):
            if char != ' ':
                s_addch(stdscr, start_y + i, start_x + j, char, color_attr)

def start_menu(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(0) # block until input
    current_option = 0
    options = ["Start Simulation", "About & Settings", "Quit"]
    selected_city = "New York, NY" # default city
    
    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        
        # titles and subtitels
        title = "C O S M O D R O M A"
        stdscr.addstr(h//2 - 5, w//2 - len(title)//2, title, curses.A_BOLD | curses.color_pair(2))
        subtitle = "your terminal planetarium"
        stdscr.addstr(h//2 - 4, w//2 - len(subtitle)//2, subtitle, curses.A_BOLD | curses.color_pair(2))
        
        # menu loop
        for i, option in enumerate(options):
            x_pos = w//2 - len(option)//2
            y_pos = h//2 - 1 + i
            if i == current_option:
                stdscr.attron(curses.A_REVERSE)
                stdscr.addstr(y_pos, x_pos, option)
                stdscr.attroff(curses.A_REVERSE)
            else:
                stdscr.addstr(y_pos, x_pos, option)
        
        # settings display
        setting_hint = f"Observation Site: {selected_city}"
        stdscr.addstr(h//2 + 3, w//2 - len(setting_hint)//2, setting_hint, curses.color_pair(1) | curses.A_DIM)
        hint = "Use UP/DOWN to select, ENTER to confirm"
        stdscr.addstr(h - 2, w//2 - len(hint)//2, hint, curses.color_pair(1))
        
        key = stdscr.getch()
        # inputs
        if key == curses.KEY_UP:
            current_option = (current_option - 1) % len(options)
        elif key == curses.KEY_DOWN:
            current_option = (current_option + 1) % len(options)
        elif key == 10: # enter
            if current_option == 0: 
                return selected_city # return the city
            if current_option == 1: 
                # settings
                in_settings = True
                current_tab = 0 # 0 = about, 1 = location
                loc_keys = list(LOCATIONS.keys())
                loc_idx = loc_keys.index(selected_city)
                
                while in_settings:
                    stdscr.clear()
                    h, w = stdscr.getmaxyx()
                    
                    # tabs
                    tabs = [" [1] About ", " [2] Settings "]
                    header_str = "".join(tabs)
                    start_x = w//2 - len(header_str)//2
                    stdscr.addstr(2, start_x, tabs[0], curses.A_REVERSE if current_tab == 0 else 0)
                    stdscr.addstr(2, start_x + len(tabs[0]), tabs[1], curses.A_REVERSE if current_tab == 1 else 0)
                    stdscr.hline(3, 2, curses.ACS_HLINE, w-4)

                    if current_tab == 0:
                        # about text
                        lines = [
                            "cosmodroma is a terminal planetarium which allows you to track and preview bright stars, planets and satellites in real time.",
                            "",
                            "Controls:",
                            "W/S: zoom in/out",
                            "E:   select body",
                            "M:   map view (satellites only)",
                            "Arrows: move view / showcase"
                        ]
                        for i, line in enumerate(lines):
                            stdscr.addstr(5+i, w//2 - len(line)//2, line)
                    else:
                        # select observation site
                        stdscr.addstr(5, w//2 - 10, "Select Observation Site:", curses.A_BOLD)
                        for i, city in enumerate(loc_keys):
                            prefix = "> " if i == loc_idx else "  "
                            attr = curses.A_REVERSE if i == loc_idx else 0
                            stdscr.addstr(7+i, w//2 - 10, f"{prefix}{city}", attr)
                            
                        # show coordinates
                        c_data = LOCATIONS[loc_keys[loc_idx]]
                        detail = f"Lat: {c_data['lat']}  Lon: {c_data['lon']}"
                        stdscr.addstr(h-4, w//2 - len(detail)//2, detail, curses.color_pair(2))

                    foot = "1/2 to switch tabs, UP/DOWN to select city, ENTER to return"
                    stdscr.addstr(h-2, w//2 - len(foot)//2, foot, curses.A_DIM)
                    
                    # controls
                    s_key = stdscr.getch()
                    if s_key == ord('1'): current_tab = 0
                    elif s_key == ord('2'): current_tab = 1
                    elif s_key == curses.KEY_UP and current_tab == 1:
                         loc_idx = (loc_idx - 1) % len(loc_keys)
                    elif s_key == curses.KEY_DOWN and current_tab == 1:
                         loc_idx = (loc_idx + 1) % len(loc_keys)
                    elif s_key == 10:
                         selected_city = loc_keys[loc_idx]
                         in_settings = False
                    elif s_key == 27:
                        in_settings = False
                        
            if current_option == 2: return None # Quit

def draw_circle(stdscr, y, x, radius, charmap, illumination=1.0, color_attr=None, has_rings=False, ring_attr=None):
    if color_attr is None:
        color_attr = curses.color_pair(1) | curses.A_BOLD # white (bold)

    center_y = int(y + 0.5)
    center_x = int(x + 0.5)

    # light direction based on phase
    cos_phase_angle = 2.0 * illumination - 1.0
    cos_phase_angle = max(-1.0, min(1.0, cos_phase_angle)) 
    lx = math.sqrt(1.0 - cos_phase_angle**2)
    lz = cos_phase_angle 

    # colour attribute
    attr = color_attr
    draw_radius_y = int(radius * 1.2) if has_rings else radius
    draw_radius_x = int(radius * 4.5) if has_rings else radius * 2

    for dy in range(-draw_radius_y, draw_radius_y + 1):
        for dx in range(-draw_radius_x, draw_radius_x + 1):
            # correct aspect ratio
            dist_sq = (dy * dy) + (dx / 2.0) ** 2
            dist = math.sqrt(dist_sq)
            is_sphere = dist <= radius
            
            # 3d sphere math
            pz_sq = -1.0
            if is_sphere:
                px = (dx / 2.0) / radius
                py = dy / radius
                pz_sq = 1.0 - px*px - py*py

                if pz_sq >= 0: pz = math.sqrt(pz_sq)

                # lambert shading - https://lavalle.pl/vr/node197.html
                dot = px * lx + pz * lz
                brightness = max(0, dot)
                    
                if brightness > 0.001:
                    # lit side
                    idx = max(1, int(brightness * (len(charmap) - 1)))
                    char = charmap[idx]
                    s_addch(stdscr, center_y + dy, center_x + dx, char, attr)
                else:
                    # dark side
                    is_grid = (center_x + dx) % 2 == 0 and (center_y + dy) % 2 == 0
                    char = '.' if is_grid else ' ' 
                    if dist > radius - 1: char = ':' 
                    s_addch(stdscr, center_y + dy, center_x + dx, char, curses.color_pair(2) | curses.A_BOLD)
            elif has_rings:
                # Ellipse equation (I have no clue what this does)
                ring_y = dy * 3.0 # higher = flatter rings
                ring_dist = math.sqrt((dx/2.0)**2 + ring_y**2)
                if radius * 1.4 < ring_dist < radius * 2.3:
                    final_ring_attr = ring_attr if ring_attr is not None else color_attr
                    s_addch(stdscr, center_y + dy, center_x + dx, '-', final_ring_attr)