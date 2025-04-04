from xyzservices import TileProvider
import folium
from skyfield.api import load, wgs84

tle_url = "https://celestrak.org/NORAD/elements/gp.php?CATNR=57582"

satellite = load.tle_file(tle_url)[0]
ts = load.timescale()
days = [0, 1, 2]
private_provider = TileProvider(
    # Tile: https://cloud.maptiler.com/maps/
    {
        "url": "https://api.maptiler.com/maps/ocean/{z}/{x}/{y}.png?key={accessToken}",
        "attribution": "(C) xyzservices",
        "accessToken": "AOgHTEOu60UAYSaAiILS",
        "name": "my_private_provider",
    }
)
m = folium.Map(
    width="100%",
    height="100%",
    tiles=private_provider,
    zoom_control=False,
    zoom_start=1,
    max_bounds=True,
)

for d in days:
    t = ts.utc(2024, 7, 15, 0, 0, range(d * 24 * 60 * 60, (d + 1) * 24 * 60 * 60, 20))
    pos = satellite.at(t)
    subpoint = wgs84.subpoint_of(pos)
    lats = subpoint.latitude.degrees
    lons = subpoint.longitude.degrees

    # prev_lat = None
    # prev_lon = None
    colors = ["#0070c0", "#ffc000", "#ff0000"]
    for lat, lon in zip(lats, lons):
        folium.CircleMarker([lat, lon], color=colors[d], radius=0.1).add_to(m)
        # if prev_lat is not None:
        #     if lat - prev_lat < 80 and lon - prev_lon < 170:
        #         folium.PolyLine(
        #             [[lat, lon], [prev_lat, prev_lon]],
        #             weight=1
        #         ).add_to(m)
        # prev_lat = lat
        # prev_lon = lon

m.save("satellite_trajectory.html")
