from skyfield.api import Star, load, wgs84
from skyfield.data import hipparcos

# configuration for spaceslop
lat = 40.7128 # this is NYC btw
long = -74.0060

def load_data(stdscr, h, w):
    ### load data
    ## jpl ephemeris
    ts = load.timescale()
    planets = load("de421.bsp")
    earth = planets["earth"]
    observer = earth + wgs84.latlon(lat, long)
    bodies = { "Mars": planets["mars"], "Venus": planets["venus"], 
               "Jupiter": planets["jupiter barycenter"], "Moon": planets["moon"],
               "Sun": planets["sun"], }

    ## star data
    ## hipparcos
    stdscr.clear()
    stdscr.addstr(h//2, w//2 - 29, "downloading Hipparcos data...")
    stdscr.refresh()
    with load.open(hipparcos.URL) as f:
        df = hipparcos.load_dataframe(f)
    bright_stars = df[df["magnitude"] <= 3.5]
    stars = Star.from_dataframe(bright_stars)
    return ts, planets, observer, bodies, stars