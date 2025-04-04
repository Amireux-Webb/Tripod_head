# Satellite Ephemeris Automatic Download + Transit Event Automatic Output
[中文](./README-zh.md)
## Instructions
After installing the dependencies in `requirements.txt`, simply run `track.py` for the following actions:

1. If `NOARD_ID` is specified in `track.py`, the TLE data will be automatically downloaded from Celestrack. The file will be saved in the `tle` subdirectory of the current directory with a filename of the Unix Timestamp when the script is run.

2. If `latitude` and `longitude` are specified in `track.py`, the script will automatically calculate the transit times of the satellites from the current time to 48 hours later, and output them to a file. The file will be saved in the `events` subdirectory of the current directory with a filename of the Unix Timestamp when the script is run. The threshold elevation angle for transit events is set to 5 degrees by default (consistent with the default behavior of gpredict software), but can be manually modified in `track.py` using the `degrees` variable.