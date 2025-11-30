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

    ## satellite data
    ## NORAD
    stdscr.addstr(h//2 + 1, w//2 - 29, "downloading NORAD data...")
    stdscr.refresh()
    sat_file = load.tle_file('https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=tle')
    satellites = {}
    count = 0
    for sat in sat_file:
        name = sat.name.upper()
        # keep known satellites
        if "ISS" in name:
            satellites["ISS"] = sat
        elif "HST" in name:
            satellites["Hubble"] = sat
        elif "TIANHE" in name:
            satellites["TIANHE"] = sat
        elif count < 20: 
            satellites[sat.name] = sat
            count += 1

    ## planetary data
    bodies = { "Mars": planets["mars"], "Venus": planets["venus"],
               "Jupiter": planets["jupiter barycenter"], 
               "Saturn": planets["saturn barycenter"],
               "Uranus": planets["uranus barycenter"],
               "Neptune": planets["neptune barycenter"],
               "Moon": planets["moon"], "Sun": planets["sun"]}
    bodies.update(satellites)

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