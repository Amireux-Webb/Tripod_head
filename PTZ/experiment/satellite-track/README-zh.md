# 卫星星历自动下载+过境事件自动输出
[English](./README.md)
## 使用方法
在安装了`requirements.txt`中的依赖后，直接运行 `track.py` 即可，行为如下：

1. 当在`track.py`中指定了 `NOARD_ID` 后，将自动从 Celestrack 下载当前的 TLE 数据。文件会保存在当前目录下的 `tle` 子目录中，文件名是运行此脚本时的Unix Timestamp。

2. 当在`track.py`中指定了 `latitude`, `longitude` (纬度、经度)后，将自动计算1中卫星从当前至48小时以后的过境时间，并输出到文件中。文件会保存在当前目录下的 `events` 子目录中，文件名是运行此脚本时的Unix Timestamp。过境事件的阈值仰角默认是5度（和gpredict软件的默认行为一致），也可以在`track.py`中手动修改`degrees`变量。
