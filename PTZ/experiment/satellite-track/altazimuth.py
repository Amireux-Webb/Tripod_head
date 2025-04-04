import os
from datetime import datetime, timezone
from os.path import abspath, dirname, join

import arrow
import requests
from skyfield.api import load, wgs84

work_dir = dirname(abspath(__file__))


def download_tle(noard_id) -> str:
    url = f"http://celestrak.org/NORAD/elements/gp.php?CATNR={noard_id}"
    response = requests.get(url)
    html_content = response.text
    utc = arrow.utcnow()
    today = utc.format("YYYY-MM-DD")
    unix_timestamp = utc.timestamp()
    tle_dir = join(work_dir, "tle", today)
    os.makedirs(tle_dir, exist_ok=True)
    files = os.listdir(tle_dir)
    for file in files:
        if file.endswith(".tle"):
            print(f"TLE cache found: {join(tle_dir, file)!r}")
            return join(tle_dir, file)
    tle_path = join(tle_dir, f"{unix_timestamp}.tle")
    with open(tle_path, "w") as html_file:
        html_file.write(html_content)
    print(f"Downloaded TLE to {tle_path!r}")
    return tle_path


def get_satellite_position(observer_lat, observer_lon, date_time):
    # Load TLE data
    satellites = load.tle_file(download_tle(57582))
    satellite = satellites[0]  # Assuming there is only one satellite in the TLE file

    # Define observer location
    observer_location = wgs84.latlon(observer_lat, observer_lon)

    # Define the time for the observation
    ts = load.timescale()
    observation_time = ts.utc(
        date_time.year,
        date_time.month,
        date_time.day,
        date_time.hour,
        date_time.minute,
        date_time.second,
    )

    # Compute the satellite position relative to the observer
    difference = satellite - observer_location
    topocentric = difference.at(observation_time)
    alt, az, distance = topocentric.altaz()

    # Compute radial velocity
    velocity = topocentric.velocity.km_per_s
    radial_velocity = velocity[
        2
    ]  # The third component of the velocity vector is the radial component

    return alt.degrees, az.degrees, distance.km, radial_velocity


# Example usage
observer_lat = 31.2304  # Latitude of observer
observer_lon = 121.4737  # Longitude of observer
date_time = datetime(
    2024, 7, 22, 12, 0, 0, tzinfo=timezone.utc
)  # Observation date and time in UTC

altitude, azimuth, distance, radial_velocity = get_satellite_position(
    observer_lat, observer_lon, date_time
)
print(f"Elvation Angle: {altitude} degrees")
print(f"Azimuth: {azimuth} degrees")
print(f"Distance: {distance} km")
print(f"Radial Velocity: {radial_velocity} km/s")
