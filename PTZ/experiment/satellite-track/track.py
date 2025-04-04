import requests
import arrow
import os
from skyfield.api import load, wgs84
from skyfield import timelib

NOARD_ID = 57582

latitude = 31.077117
longitude = 121.381141

degrees = 5

if __name__ == "__main__":
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    tle_dir = os.path.join(script_dir, "tle")
    events_dir = os.path.join(script_dir, "events")
    os.makedirs(tle_dir, exist_ok=True)
    os.makedirs(events_dir, exist_ok=True)

    url = f"http://celestrak.org/NORAD/elements/gp.php?CATNR={NOARD_ID}"
    response = requests.get(url)
    html_content = response.text

    utc = arrow.utcnow()
    unix_timestamp = utc.timestamp()
    tle_path = os.path.join(tle_dir, f"{unix_timestamp}.tle")
    with open(tle_path, "w") as html_file:
        html_file.write(html_content)

    ts = load.timescale()
    place = wgs84.latlon(latitude, longitude)

    # from now to 2 days later considering timezone
    t0 = ts.from_datetime(utc.datetime)
    t1 = ts.from_datetime(utc.shift(days=+2).datetime)

    satellite = load.tle_file(tle_path)[0]
    t, events = satellite.find_events(place, t0, t1, altitude_degrees=degrees)
    t: list[timelib.Time]
    event_names = f"rise above {degrees}°", "culminate", f"set below {degrees}°"
    events_path = os.path.join(events_dir, f"{unix_timestamp}.events")
    with open(events_path, "wt") as f:
        for ti, event in zip(t, events):
            local_time = (
                arrow.get(ti.utc_datetime())
                .to("Asia/Shanghai")
                .format("YYYY-MM-DD HH:mm:ss ZZ")
            )
            name = event_names[event]
            f.write(f"{local_time} {name}\n")
            if name.startswith("set"):
                f.write("\n")
