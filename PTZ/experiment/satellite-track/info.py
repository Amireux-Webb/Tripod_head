from skyfield.api import load, wgs84
from numpy import pi

tle_url = "https://celestrak.org/NORAD/elements/gp.php?CATNR=57582"

satellite = load.tle_file(tle_url)[0]
ts = load.timescale()

t = ts.utc(2024, 7, 15, 0, 0, 0)

# inclination
print(satellite.model.inclo / 2 / pi * 360)
print(satellite.model.nodeo / 2 / pi * 360)
