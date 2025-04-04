## 此程序主要实现，在一年时间里，不同仰角范围内的过境次数，以比较概率次数

import os
from datetime import datetime, timedelta
from os.path import abspath, dirname, join

import numpy as np
from skyfield.api import load, wgs84

work_dir = dirname(abspath(__file__))
parent_dir = os.path.dirname(work_dir)

Reyk = wgs84.latlon(64.0848, -21.5624)
Shanghai = wgs84.latlon(31.1343, 121.2829)  # 31°13′43″N 121°28′29″E
Singapore = wgs84.latlon(1.17, 103.50)  # 1°17′N 103°50′E
Melbourne = wgs84.latlon(-37.4849, 144.5747)  # 37°48′49″S 144°57′47″E

places = {
    "Reyk": Reyk,
    "Shanghai": Shanghai,
    "Singapore": Singapore,
    "Melbourne": Melbourne,
}
ts = load.timescale()

for place_name, place in places.items():
    # 统计不同区间的过境次数
    print(place_name)
    intervals = np.arange(0, 100, 10)
    counts = {f"{i}-{i+10}": 0 for i in intervals[:-1]}
    total_days = 0

    for idx, SAT_TIME in enumerate(os.listdir(join(parent_dir, "data", "tle"))):
        # print(f"Skipping {join(parent_dir, "data", "tle", SAT_TIME)!r}")
        tle_dir = join(parent_dir, "data", "tle", SAT_TIME)
        for file in os.listdir(tle_dir):
            if file.endswith(".tle"):
                tle_file = file
                break
        if tle_file:
            total_days += 1
            with open(join(tle_dir, tle_file), "r") as file:
                lines = file.readlines()
                line1 = lines[1].strip()
                year = int(line1[18:20])
                day_of_year = float(line1[20:32])
                year += 2000
                date = datetime(year, 1, 1) + timedelta(days=day_of_year - 1)
                # print("Datetime:", date.strftime('%Y-%m-%d'))
                # 加载卫星数据和时间标度
                satellite = load.tle_file(join(tle_dir, tle_file))[
                    0
                ]  # 从星历文件加载卫星方位
                t0 = ts.utc(date.year, date.month, date.day)
                t1 = ts.utc(date.year, date.month, date.day + 1)
                # 查找过境事件
                t, events = satellite.find_events(place, t0, t1, altitude_degrees=0.0)
                # 获取每次过境的最大仰角
                event_names = ["rise", "culminate", "set"]
                for i in range(len(events)):
                    if event_names[events[i]] == "culminate":
                        max_alt_time = t[i]
                        topocentric = (satellite - place).at(max_alt_time).altaz()
                        max_alt = topocentric[0].degrees
                        print(max_alt)
                        for j in intervals[:-1]:
                            if j <= max_alt < j + 10:
                                counts[f"{j}-{j+10}"] += 1
                                break
        else:
            print("No .tle file found in the directory.")

    for j in intervals[:-1]:
        counts[f"{j}-{j+10}"] = counts[f"{j}-{j+10}"] / total_days

    # 打印结果
    print(f"总天数{total_days}")
    total_num = 0
    for k, v in counts.items():
        print(f"仰角区间 {k} 度的过境次数: {v}")
        total_num += v

    print(f"总次数{total_num}")
