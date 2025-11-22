import curses
import math

def s_addch(stdscr, y, x, char, attr=0): # safe character drawing
    h, w = stdscr.getmaxyx()
    if 0 <= y < h and 0 <= x < w: # only if it is within bounds.
        try:
            stdscr.addch(int(y), int(x), char, attr)
        except:
            pass

def start_menu(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(0) # block until input
    current_option = 0
    options = ["Start Simulation", "About", "Quit"]
    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        # titles
        title = "C O S M O D R O M A"
        stdscr.addstr(h//2 - 4, w//2 - len(title)//2, title, curses.A_BOLD | curses.color_pair(2))
        subtitle = "your telescope to the stars"
        stdscr.addstr(h//2 - 3, w//2 - len(subtitle)//2, subtitle, curses.A_BOLD | curses.color_pair(2))
        # options
        for i, option in enumerate(options):
            x_pos = w//2 - len(option)//2
            y_pos = h//2 - 1 + i
            if i == current_option:
                stdscr.attron(curses.A_REVERSE)
                stdscr.addstr(y_pos, x_pos, option)
                stdscr.attroff(curses.A_REVERSE)
            else:
                stdscr.addstr(y_pos, x_pos, option)
        
        # instructions
        hint = "Use UP/DOWN to select, ENTER to confirm"
        stdscr.addstr(h - 2, w//2 - len(hint)//2, hint, curses.color_pair(1))
        key = stdscr.getch()
        
        # inputs
        if key == curses.KEY_UP:
            current_option = (current_option - 1) % len(options)
        elif key == curses.KEY_DOWN:
            current_option = (current_option + 1) % len(options)
        elif key == 10: # enter key
            if current_option == 0: return True #  enter
            if current_option == 1: 
                # about
                stdscr.clear()
                msg = "this is your very own telescope"
                stdscr.addstr(h//2, w//2 - len(msg)//2, msg)
                stdscr.refresh()
                stdscr.getch()
            if current_option == 2: return False # quit

def draw_circle(stdscr, y, x, radius, charmap, illumination=1.0):
    center_y = int(y + 0.5)
    center_x = int(x + 0.5)

    # light direction based on phase
    cos_phase_angle = 2.0 * illumination - 1.0
    cos_phase_angle = max(-1.0, min(1.0, cos_phase_angle)) 
    lx = math.sqrt(1.0 - cos_phase_angle**2)
    lz = cos_phase_angle 

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
            
            if brightness > 0.001:
                # lit side
                idx = max(1, int(brightness * (len(charmap) - 1)))
                char = charmap[idx]
                s_addch(stdscr, center_y + dy, center_x + dx, char, attr)
            else:
                # dark hemisphere
                # make a grid pattern
                is_grid = (center_x + dx) % 2 == 0 and (center_y + dy) % 2 == 0
                char = '.' if is_grid else ' ' 
                if dist > radius - 1: char = ':' 
                s_addch(stdscr, center_y + dy, center_x + dx, char, curses.color_pair(2) | curses.A_BOLD)