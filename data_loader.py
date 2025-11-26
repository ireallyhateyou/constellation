from skyfield.api import Star, load, wgs84
from skyfield.data import hipparcos

def load_data(stdscr, h, w, lat=40.7128, long=-74.0060):
    ### load data
    ## jpl ephemeris
    ts = load.timescale()
    planets = load("de421.bsp")
    earth = planets["earth"]
    observer = earth + wgs84.latlon(lat, long)
    topos_observer = wgs84.latlon(lat, long)
    ## iss tle data
    stdscr.addstr(h//2 + 1, w//2 - 29, "downloading ISS TLE data...")
    stdscr.refresh()
    stations_list = load.tle_file('https://celestrak.org/NORAD/elements/stations.txt')
    stations = {s.name: s for s in stations_list}
    iss = stations['ISS (ZARYA)']
    bodies = { "Mars": planets["mars"], "Venus": planets["venus"],
               "Jupiter": planets["jupiter barycenter"], 
               "Saturn": planets["saturn barycenter"],
               "Uranus": planets["uranus barycenter"],
               "Neptune": planets["neptune barycenter"],
               "Moon": planets["moon"], "Sun": planets["sun"], "ISS": iss}

    ## satellite data
    ## NORAD
    stdscr.addstr(h//2 + 1, w//2 - 29, "downloading NORAD data...")
    stdscr.refresh()
    satellites = load.tle_file('https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=tle')
    sat_dict = {s.name: s for s in satellites}

    ## star data
    ## hipparcos
    stdscr.clear()
    stdscr.addstr(h//2, w//2 - 29, "downloading Hipparcos data...")
    stdscr.refresh()
    with load.open(hipparcos.URL) as f:
        df = hipparcos.load_dataframe(f)
    bright_stars = df[df["magnitude"] <= 3.5]
    stars = Star.from_dataframe(bright_stars)
    return ts, planets, observer, topos_observer, bodies, stars 