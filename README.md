LEHome
======

LEHome 是一套完整的智能家居方案。LEHome拥有以下特性：

1. 简单的语音命令编程
2. ibeacon室内定位
3. 高度模块设计
4. 红外控制、开关控制、传感器采集

安装
====

软件

服务端

LEHome 服务端基于Python，需要安装以下依赖：

    - tornado
    - pyzmq
    - numpy
    - scipy
    - pyaudio
    - fysom
    - mplayer
    - sox

客户端

目前LEHome仅实现了Android客户端，详见项目地址：

[LEHome android 客户端]()

硬件

要完整地运行本项目，需要准备以下硬件：

1. reco WIFI插座 * n
2. 蓝牙4.0适配器 * 2
3. ibeacon模块   * 1
4. 蓝牙音箱      * 1
5. 红外模块      * 1
6. zigbee传感器  * 2

架构
====

组成

命令

解析过程

模块
====


