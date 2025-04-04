from socket import *
import time
import binascii
from .logger import logger

#各类所需协议对照表
work_mode_dict = { # 输出对应的工作模式
    0x01: "云台自检中",
    0x02: "区域扫描进行中",
    0x03: "区域扫描暂停中",
    0x04: "区域扫描恢复中",
    0x05: "区域扫描关闭中",
    0x06: "预置位扫描中",
    0x07: "预置位扫描暂停中",
    0x08: "预置位扫描恢复中",
    0x09: "预置位扫描关闭中",
    0x10: "水平电压采集中",
    0x11: "垂直电压采集中",
    0x12: "水平、垂直电压采集中",
    0x13: "水平位置更新出错",
    0x14: "垂直位置更新出错",
    0x15: "水平、垂直位置更新出错",
    0x16: "电机低温无法转动",
    0xfa: "水平电机低温故障",
    0xfb: "垂直电机低温故障",
    0xfc: "水平电机故障无法转动",
    0xfd: "垂直电机故障无法转动",
    0xfe: "所有电机故障无法转动",
    0x00: "常规正常模式"
}
response_dict = { # 回复工作状态目录
    0x21: "水平电机状态",
    0x22: "水平霍尔传感器状态",
    0x23: "水平光电开关位置更新状态",
    0x24: "垂直电机状态",
    0x25: "垂直霍尔传感器状态",
    0x26: "垂直光电开关位置更新状态",
    0x27: "温度状态",
    0x28: "电压状态",
    0x29: "电源状态",
    0x2A: "电流状态"
}

# 初始化UDP连接
def init_udp_connection(ip='192.168.8.200', port=6666, local_ip= '192.168.8.222', local_port= 139):
    sock = socket(AF_INET, SOCK_DGRAM)
    local_addr = (local_ip, local_port)
    sock.bind(local_addr)  # 绑定本地IP和端口
    return sock, (ip, port)

# 发送PELCO-D协议
def send_command(sock, addr, command_data, add, message=False):
    start_byte = 0xFF
    # add = 0x01  # 云台的独特地址，固定为1
    checksum = (add + sum(command_data)) & 0x00FF
    packet = [start_byte, add] + command_data + [checksum]
    packet_hex_str = ''.join(f'{byte:02x}  ' for byte in packet)  # 打印即将发送的数据包为16进制字符串格式
    if message:
        print(f"Sending packet: {packet_hex_str}")
    try:
        sock.sendto(bytearray(packet), addr)
    except Exception as e:
        print(f"发送数据包时发生错误: {e}")
    # time.sleep(0.1)
  
# 查询工作模式
def query_work_mode(sock, addr, add):
    command_data = [0xe0, 0x00, 0x00, 0x00]  # 查询工作模式命令 (参考手册 5.2.5.1)
    print()
    print("Querying work mode", end=' >>> ')
    send_command(sock, addr, command_data, add)
    sock.settimeout(5.0)
    try:
        response, _ = sock.recvfrom(1024)
        work_mode = response[3]  # 获取返回数据中的工作模式
        # 如果工作模式在字典中，则输出对应描述
        work_mode_desc = work_mode_dict.get(work_mode, f"未知模式 (值: {work_mode})")
        # 显示收到的数据包及工作模式
        print(f"Recvfrom packet: {''.join(f'{byte:02x}  ' for byte in response)}and work mode is {work_mode_desc}")
        return work_mode_desc
    except timeout:
        print("接收工作模式数据超时")
    return None

# 查询工作状态
def query_work_status(sock, addr, add):
    command_data = [0xdd, 0x00, 0x00, 0x00]  # 查询工作状态命令
    print()
    print("Querying work status", end=' >>> ')
    send_command(sock, addr, command_data, add)
    sock.settimeout(5.0)

    try:
        # 设定需要接收的状态包数量（可以根据实际需要调整）
        num_packets = 13

        for i in range(num_packets):
            response, _ = sock.recvfrom(1024)
            response_str = ' '.join(f'{byte:02x}' for byte in response)
            response_type = response[2]
            if response_type == 0x21:  # HoriMotor 状态
                hm_state = "正常" if response[3] == 0 else "故障"
                hori_dir = "右转" if response[4] == 4 else "左转" if response[4] == 3 else "未知方向"
                hori_rot = "刹车" if response[5] == 0 else "转动"
                print(f"Recvfrom packet: {''.join(f'{byte:02x}  ' for byte in response)}and 水平转动状态：{hm_state} {hori_dir} {hori_rot}")

            elif response_type == 0x22:  # HoriHall 状态
                hhall_state = "正常" if response[3] == 0 else "霍尔传感器故障"
                print(f"Recvfrom packet: {''.join(f'{byte:02x}  ' for byte in response)}and 水平电机霍尔: {hhall_state}")

            elif response_type == 0x24:  # VertMotor 状态
                vm_state = "正常" if response[3] == 0 else "故障"
                vert_dir = "上转" if response[4] == 1 else "下转" if response[4] == 2 else "未知方向"
                vert_rot = "刹车" if response[5] == 0 else "转动"
                print(f"Recvfrom packet: {''.join(f'{byte:02x}  ' for byte in response)}and 垂直转动状态：{vm_state} {vert_dir} {vert_rot}")

            elif response_type == 0x25:  # VertHall 状态
                vhall_state = "正常" if response[3] == 0 else "霍尔传感器故障"
                print(f"Recvfrom packet: {''.join(f'{byte:02x}  ' for byte in response)}and 垂直电机霍尔: {vhall_state}")

            elif response_type == 0x27:  # Temp 状态
                temp_state = "正常" if response[3] == 0 else "高温故障"
                temperature = ((response[4] << 8) + response[5]) / 100.0
                print(f"Recvfrom packet: {''.join(f'{byte:02x}  ' for byte in response)}and 查询云台温度成功，当前温度: {temperature:.1f} °C")

            elif response_type == 0x28:  # Volt 状态
                vstate = "正常" if response[3] == 0 else "工作电压异常"
                voltage = ((response[4] << 8) + response[5]) / 100.0
                print(f"Recvfrom packet: {''.join(f'{byte:02x}  ' for byte in response)}and 查询云台电压成功，当前电压: {voltage:.2f} V")

            elif response_type == 0x2A:  # Current 状态
                istate = "正常" if response[3] == 0 else "电流异常"
                current = ((response[4] << 8) + response[5]) / 100.0
                print(f"Recvfrom packet: {''.join(f'{byte:02x}  ' for byte in response)}and 查询云台电流成功，当前电流: {current:.1f} A")

            elif response_type == 0x29:  # Power 状态
                vis = "电源1打开" if response[3] == 1 else "电源1关闭"
                inf = "电源2打开" if response[4] == 1 else "电源2关闭"
                print(f"Recvfrom packet: {''.join(f'{byte:02x}  ' for byte in response)}and 顶部电源1：{vis} 顶部电源2：{inf}")

            elif response_type == 0x2F:  # 光电开关状态
                switch_state = "正常" if response[3] == 0 else "故障"
                print(f"Recvfrom packet: {''.join(f'{byte:02x}  ' for byte in response)}and 光电开关状态 {switch_state}")

            else:
                print(f"Recvfrom packet: {''.join(f'{byte:02x}  ' for byte in response)}and 未知的状态类型: {response_type}")

    except timeout:
        print("接收工作状态数据超时")
    return None

# 查询温度
def query_temperature(sock, addr, add):
    command_data = [0xd6, 0x00, 0x00, 0x00]  # 查询温度命令 (参考手册 5.2.7.1)
    print()
    print("Querying temperature",end=' >>> ')
    send_command(sock, addr, command_data, add)
    # response, _ = sock.recvfrom(1024)
    # print(response)
    sock.settimeout(5.0)
    try:
        response, _ = sock.recvfrom(1024)
        h_temp = response[3]
        l_temp = response[4]
        temperature = ((h_temp << 8) + l_temp) / 100.0
        # print(f"Temperature is {temperature}", chr(176), "C")
        print(f"Recvfrom packet: {''.join(f'{byte:02x}  ' for byte in response)}and Temperature is {temperature}", chr(176), "C")
        return temperature
    except timeout:
        print("接收温度数据超时")
    return None

# 角度定位
def set_angle_position(sock, addr, add, elevation=None, azimuth=None, message=False):
    if azimuth is not None:
        # 水平角度指令
        h_angle = azimuth
        h_angle_value = int(h_angle * 100)  # 角度放大100倍并取整
        h_high = (h_angle_value >> 8) & 0xFF  # 高八位
        h_low = h_angle_value & 0xFF  # 低八位
        command_data = [0x00, 0x4b, h_high, h_low]  # 垂直角度指令
        if message:
            print()
            print(f"水平角度定位 {azimuth:.2f}°",end=' >>> ')
        send_command(sock, addr, command_data, add, message)
        sock.settimeout(5.0)
        try:
            response, _ = sock.recvfrom(1024)
            if message:
                print(f"Recvfrom packet: {''.join(f'{byte:02x}  ' for byte in response)}")
        except timeout:
            print("接收水平角度定位确认超时")

    if elevation is not None:
        # 垂直角度指令
        v_angle = elevation - 90
        v_angle_value = int(v_angle * 100)  # 角度放大100倍并取整
        if v_angle_value < 0:
            v_angle_value = -v_angle_value ^ 0xFFFF
            v_angle_value = v_angle_value + 1 # 计算16位补码表示
        v_high = (v_angle_value >> 8) & 0xFF  # 高八位
        v_low = v_angle_value & 0xFF  # 低八位
        command_data = [0x00, 0x4d, v_high, v_low]  # 垂直角度指令
        if message:
            print()
            print(f"垂直角度定位 {elevation:.2f}°",end=' >>> ')
        send_command(sock, addr, command_data, add, message)
        sock.settimeout(5.0)
        try:
            response, _ = sock.recvfrom(1024)
            if message:
                print(f"Recvfrom packet: {''.join(f'{byte:02x}  ' for byte in response)}")
        except timeout:
            print("接收垂直角度定位确认超时")


# 云台自检
def full_self_check(sock, addr, add):
    command_data = [0x00, 0x00, 0x00, 0x00, 0x00]  # 云台全自检命令 (参考手册 5.2.13 云台全范围自检)
    send_command(sock, addr, command_data, add)

# 方向控制  
def direction_control(sock, addr, command_type, add, h_speed=0x00, v_speed=0x00):
    # 根据输入的0-7指令类型确定控制方向的命令
    directions = {
        0: [0x00, 0x00, 0x00, 0x00],  # 停止
        1: [0x00, 0x08, 0x00, v_speed],  # 向上
        2: [0x00, 0x10, 0x00, v_speed],  # 向下
        3: [0x00, 0x04, h_speed, 0x00],  # 向左
        4: [0x00, 0x02, h_speed, 0x00],  # 向右
        5: [0x00, 0x0C, h_speed, v_speed],  # 左上
        6: [0x00, 0x0A, h_speed, v_speed],  # 右上
        7: [0x00, 0x14, h_speed, v_speed],  # 左下
        8: [0x00, 0x12, h_speed, v_speed],  # 右下
    }
    if command_type in directions:
        command_data = directions[command_type]
        send_command(sock, addr, command_data, add)
    else:
        print("无效的方向指令类型，必须在0-7之间")

# 改变云台地址（慎用！！）
def modify_ptz_address(sock, addr):
    start_byte = 0xFF
    add = 0x00  # 云台的独特地址，固定为1
    cmd_type = 0x01
    func = 0x10
    cmd_len = 0x0100  # 这个是 2 字节长度
    head_crc = 0x110100  # 这个是 3 字节长度
    data = 0x31 
    crc = 0x540100  # 这个是 3 字节长度
    end_byte = 0x16

    # 将每一个字段拆分为字节并加入数据包列表
    packet = [
        start_byte,
        add,
        cmd_type,
        func,
        0x01,   # 拆分 cmd_len 的高字节
        0x00,          # 拆分 cmd_len 的低字节
        0x11, # 拆分 head_crc 的高字节
        0x01,  # 拆分 head_crc 的中间字节
        0x00,         # 拆分 head_crc 的低字节
        0x31,
        0x54,      # 拆分 crc 的高字节
        0x01,       # 拆分 crc 的中间字节
        0x00,              # 拆分 crc 的低字节
        end_byte
    ]
    # 打印即将发送的数据包为16进制字符串格式
    packet_hex_str = ''.join(f'{byte:02x}' for byte in packet)
    print(f"Sending packet: {packet_hex_str}")

    try:
        # 将包转换为 bytearray 后发送
        sock.sendto(bytearray(packet), addr)
        response, addr = sock.recvfrom(1024)
        print(response.decode())
    except Exception as e:
        print(f"发送数据包时发生错误: {e}")

    time.sleep(0.1)


