import os
from datetime import datetime, timezone, timedelta
from os.path import abspath, dirname, join
import numpy as np
import matplotlib.pyplot as plt
from skyfield.api import load, EarthSatellite, wgs84
from utils.logger import logger
from utils.ptz_command import init_udp_connection, full_self_check, query_temperature, direction_control, query_work_mode, query_work_status, set_angle_position
from skyfield import timelib
import requests
import arrow
from socket import *
import time
import binascii


# 起始位置和姿态（默认起始向北，仰角0度）
Shanghai_location = wgs84.latlon(31.1343, 121.2829)  # 31°13′43″N 121°28′29″E
azimuth_ptz = 0 # 初始云台北向顺时针多少度
# elevation_ptz = 0 # 初始云台仰角多少度->要求初始云台找平

# 起始卫星参数
NOARD_ID = 60745 # SX-1

# 云台参数
ip= '192.168.8.200'
port= 6666
add = 0x01  #云台独特地址

# 主机参数
local_ip = '192.168.8.222' # 监听所有本地接口
local_port = 139       # 本地绑定的端口

# 其他参数
ts = load.timescale()
tick_time=200 # 采样周期，单位毫秒
n= 1 # 循环次数
elevation_judge = 60 # 仰角阈值

def download_tle(noard_id) -> str: # 下载tle文件
    url = f"http://celestrak.org/NORAD/elements/gp.php?CATNR={noard_id}"
    response = requests.get(url)
    html_content = response.text
    utc = arrow.utcnow()
    today = utc.format("YYYY-MM-DD")
    # unix_timestamp = utc.timestamp()
    tle_dir = join(data_dir, "tle", f"{noard_id}", today)
    os.makedirs(tle_dir, exist_ok=True)
    files = os.listdir(tle_dir)
    for file in files:
        if file == f"{today}.tle":
            logger.info(f"TLE cache found: {join(tle_dir, file)!r}")
            return join(tle_dir, file)
    tle_path = join(tle_dir, f"{today}.tle")
    with open(tle_path, "w") as html_file:
        html_file.write(html_content)
    logger.info(f"Downloaded TLE to {tle_path!r}")
    return tle_path


def get_satellite_position(tle_path, observer_location, tick_time): # 获得卫星轨迹
    """
    Get satellite position and find the next pass event.

    Parameters:
    tle_path: str - Path to the TLE file.
    observer_location: wgs84.latlon - Observer's location.
    tick_time: int - Angle sampling period in milliseconds.

    Returns:
    alt_array, az_array: numpy.ndarray - Altitude and azimuth angles for each sample during the pass.
    """
    # Load satellite data
    satellite = load.tle_file(tle_path)[0]
    
    # Get current UTC time
    start_time = datetime.now(timezone.utc)
    logger.info(f"The current time is {start_time}")

    # Find the next pass event
    t0 = ts.from_datetime(start_time)
    t1 = ts.from_datetime(start_time + timedelta(days=1))
    t, events = satellite.find_events(observer_location, t0, t1, altitude_degrees=0.0)
    
    for ti, event in zip(t, events):
        if event == 0:  # Rise event
            rise_time = ti.utc_datetime()
            # Find the corresponding culmination event
            idx = list(events).index(1, list(events).index(event))
            culminate_time = t[idx].utc_datetime()
            set_time = t[idx + 1].utc_datetime()  # Set time
            topocentric = (satellite - observer_location).at(t[idx]).altaz()
            max_altitude_degrees = topocentric[0].degrees

            # Print rise time and maximum altitude
            logger.info(f"Next pass rise time: {rise_time}")
            logger.info(f"Maximum altitude time: {culminate_time}")
            logger.info(f"Next pass set time: {set_time}")
            logger.info(f"Maximum altitude: {max_altitude_degrees:.2f} degrees")

            # Calculate the number of samples
            delta_milliseconds = int((set_time - rise_time).total_seconds()) * 1000
            num_samples = delta_milliseconds // tick_time + 1
            time_idxs = range(num_samples)

            # Generate list of sample times
            times_list = [rise_time + timedelta(milliseconds=i * tick_time) for i in range(num_samples)]
            times = ts.utc(times_list)

            # Calculate altitude and azimuth for each sample time
            difference = satellite - observer_location
            topocentric = difference.at(times)
            altitudes, azimuths, _ = topocentric.altaz()

            # Store results in arrays
            alt_array = altitudes.degrees
            az_array = azimuths.degrees
            
            # print_picture
            altaz_dir = dirname(tle_path)
            plt.figure(figsize=(10, 6))
            plt.plot(time_idxs, alt_array, label=f"Elevation ({max_altitude_degrees})")
            plt.xlabel("Time (UTC)")
            plt.ylabel("Elevation (degrees)")
            plt.grid(True)
            plt.legend()
            plt.savefig(join(altaz_dir, f"time_elevation.png"))
            plt.close()

            plt.figure(figsize=(10, 6))
            plt.plot(time_idxs, az_array, label=f"Elevation Rate ({max_altitude_degrees})", color='r')
            plt.xlabel("Time (UTC)")
            plt.ylabel("Elevation Rate (degrees per second)")
            plt.grid(True)
            plt.legend()
            plt.savefig(join(altaz_dir, f"azimuth.png"))
            plt.close()
            
            plt.figure(figsize=(10, 6))
            ax = plt.subplot(111, polar=True)
            ax.plot(np.radians(az_array), 90 - alt_array, marker='o', linestyle='-')
            ax.set_theta_zero_location('N')  # Set 0 degrees to North
            ax.set_theta_direction(-1)  # Set direction to clockwise
            plt.title('Satellite Sky Path During Pass')
            plt.grid(True)
            plt.savefig(join(altaz_dir, f"sky_track.png"))
            plt.close()
            
            return alt_array, az_array, rise_time

    print("No pass events in the next 24 hours.")
    return None, None, None

def get_satellite_position_angle(tle_path, observer_location, tick_time, elevation_judge): # 获得卫星轨迹
    # Load satellite data
    satellite = load.tle_file(tle_path)[0]
    
    # Get current UTC time
    start_time = datetime.now(timezone.utc)
    logger.info(f"The current time is {start_time}")

    # Find the next pass event
    t0 = ts.from_datetime(start_time)
    t1 = ts.from_datetime(start_time + timedelta(days=21))
    t, events = satellite.find_events(observer_location, t0, t1, altitude_degrees=0.0)
    
    for ti, event in zip(t, events):
        if event == 0:  # Rise event
            rise_time = ti.utc_datetime()
        elif event == 1:  # Culminate event
            culminate_time = ti.utc_datetime()
            topocentric = (satellite - observer_location).at(ti).altaz()
            max_altitude_degrees = topocentric[0].degrees
        elif event == 2:  # Set event
            set_time = ti.utc_datetime()

            # Check if the maximum altitude is greater than elevation_judge degrees
            if max_altitude_degrees > elevation_judge:
                # Print rise time and maximum altitude
                logger.info(f"Next pass rise time: {rise_time}")
                logger.info(f"Maximum altitude time: {culminate_time}")
                logger.info(f"Next pass set time: {set_time}")
                logger.info(f"Maximum altitude: {max_altitude_degrees:.2f} degrees")

                # Calculate the number of samples
                delta_milliseconds = int((set_time - rise_time).total_seconds()) * 1000
                num_samples = delta_milliseconds // tick_time + 1
                time_idxs = range(num_samples)

                # Generate list of sample times
                times_list = [rise_time + timedelta(milliseconds=i * tick_time) for i in range(num_samples)]
                times = ts.utc(times_list)

                # Calculate altitude and azimuth for each sample time
                difference = satellite - observer_location
                topocentric = difference.at(times)
                altitudes, azimuths, _ = topocentric.altaz()

                # Store results in arrays
                alt_array = altitudes.degrees
                az_array = azimuths.degrees

                # print_picture
                altaz_dir = dirname(tle_path)
                altaz_dir = join(altaz_dir,f"judge_{elevation_judge}")
                os.makedirs(altaz_dir, exist_ok=True)
                plt.figure(figsize=(10, 6))
                plt.plot(time_idxs, alt_array, label=f"Elevation ({max_altitude_degrees})")
                plt.xlabel("Time (UTC)")
                plt.ylabel("Elevation (degrees)")
                plt.grid(True)
                plt.legend()
                plt.savefig(join(altaz_dir, f"time_elevation_{elevation_judge}.png"))
                plt.close()

                plt.figure(figsize=(10, 6))
                plt.plot(time_idxs, az_array, label=f"Elevation Rate ({max_altitude_degrees})", color='r')
                plt.xlabel("Time (UTC)")
                plt.ylabel("Elevation Rate (degrees per second)")
                plt.grid(True)
                plt.legend()
                plt.savefig(join(altaz_dir, f"azimuth_{elevation_judge}.png"))
                plt.close()
                
                plt.figure(figsize=(10, 6))
                ax = plt.subplot(111, polar=True)
                ax.plot(np.radians(az_array), 90 - alt_array, marker='o', linestyle='-')
                ax.set_theta_zero_location('N')  # Set 0 degrees to North
                ax.set_theta_direction(-1)  # Set direction to clockwise
                plt.title('Satellite Sky Path During Pass')
                plt.grid(True)
                plt.savefig(join(altaz_dir, f"sky_track_{elevation_judge}.png"))
                plt.close()
                
                return alt_array, az_array, rise_time
    
    print("No pass events in the next 24 hours with max altitude > 60 degrees.")
    return None, None, None


def main():   
    # 读取tle文件并更新
    tle_path = download_tle(NOARD_ID)
    
    # 采集最近的N次过境数据
    for i in range(n):
        # 读取现在时间，寻找最近一次过境事件
        # elevations, azimuths, rise_time = get_satellite_position(tle_path, Shanghai_location, tick_time)
        # 读取现在时间，寻找最近一次大于n度的过境事件
        
        elevations, azimuths, rise_time = get_satellite_position_angle(tle_path, Shanghai_location, tick_time, elevation_judge)
        
        # 连接云台，读取工作模式和工作状态，并对准卫星到达的初始角度
        if elevations is not None and azimuths is not None:
            sock, ptz_addr = init_udp_connection(ip, port, local_ip, local_port)
            logger.info(f"Connection established with{sock, ptz_addr}")
            query_work_mode(sock, ptz_addr, add)
            query_work_status(sock, ptz_addr, add)
            # full_self_check(sock, address, add)
        else:
            logger.error("No pass events in the next 24 hours.")
            return
        
        # 开始控制云台，使云台指向卫星
        start_azimuth= azimuths[0] - azimuth_ptz
        start_elevation = elevations[0]
        set_angle_position(sock, ptz_addr, add, start_elevation, start_azimuth, message=True)
        
        # 等待到卫星升起的时刻，考虑程序执行时间
        logger.info(f"Waiting for satellite rise at {rise_time}")
        # while datetime.now(timezone.utc) < rise_time:
        #     # 循环等待直到达到升起时间，避免 sleep 时间影响精确性
        #     time.sleep(0.1)  # 检查当前时间，使用较小的睡眠时间间隔以减少 CPU 占用并保持精确度

        # 按照采样周期开始跟踪卫星
        logger.info("Starting to track the satellite...")
        tracking_start_time = time.time()  # 记录跟踪的起始时间

        for i in range(len(elevations)):
            # 获取当前时刻应追踪的角度
            current_azimuth = azimuths[i] - azimuth_ptz
            current_elevation = elevations[i]

            # 调用 set_angle_position 函数来设定新的角度
            set_angle_position(sock, ptz_addr, add, current_elevation, current_azimuth, message=True)

            # 确保每次执行都是在精确的 tick_time 间隔
            next_time = tracking_start_time + (i + 1) * (tick_time / 1000.0)
            current_time = time.time()
            sleep_time = max(0, next_time - current_time)
            if sleep_time > 0:
                time.sleep(sleep_time)  # 保证时间间隔为 tick_time
        
        logger.info("Finished tracking the satellite.")
    
    return


if __name__ == "__main__":
    #文档位置
    parent_dir = dirname(dirname(abspath(__file__)))
    data_dir = join(parent_dir,"data")    
    
    main()    
