import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from skyfield.api import load, wgs84

# Load satellite TLE data
tle_url = "https://celestrak.org/NORAD/elements/gp.php?CATNR=57582"
satellite = load.tle_file(tle_url)[0]
ts = load.timescale()

# Define time range and compute positions
days = [0, 1, 2]
positions = []

for d in days:
    t = ts.utc(2024, 7, 15, 0, 0, range(d * 24 * 60 * 60, (d + 1) * 24 * 60 * 60, 20))
    pos = satellite.at(t)
    subpoint = wgs84.subpoint_of(pos)
    lats = subpoint.latitude.degrees
    lons = subpoint.longitude.degrees
    positions.append((lats, lons))

# Create a Mollweide projection plot
fig = plt.figure(figsize=(10, 5))
ax = fig.add_subplot(1, 1, 1, projection=ccrs.Mollweide())
ax.set_global()
ax.coastlines()

# Plot the satellite positions
colors = ["#0070c0", "#ffc000", "#ff0000"]
for d, (lats, lons) in enumerate(positions):
    ax.scatter(lons, lats, color=colors[d], s=1, transform=ccrs.PlateCarree())

# Save the figure as a JPEG file
plt.savefig("satellite_trajectory_mollweide.jpg", dpi=300)
plt.show()
