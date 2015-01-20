                                                                       
        _/        _/_/_/_/  _/    _/    _/_/    _/      _/  _/_/_/_/   
       _/        _/        _/    _/  _/    _/  _/_/  _/_/  _/          
      _/        _/_/_/    _/_/_/_/  _/    _/  _/  _/  _/  _/_/_/       
     _/        _/        _/    _/  _/    _/  _/      _/  _/            
    _/_/_/_/  _/_/_/_/  _/    _/    _/_/    _/      _/  _/_/_/_/       
                                                                                 
    ================================================================

LEHome 是一套完整的开源智能家居方案。LEHome拥有以下特性：

1. 简单的控制命令编程
2. ibeacon室内定位
3. 高度模块设计
4. 红外控制、开关控制、传感器采集
5. android，web app，微信版客户端

项目地址：[https://github.com/legendmohe/LEHome](https://github.com/legendmohe/LEHome)

部署
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

down下来后，配置init.json（后面会说明如何配置），然后在根目录下运行./start.sh即可（先用chmod添加执行权限）。

客户端

目前LEHome实现了Android，web app，微信版客户端，如有需要可与我联系legendmohe@foxmail.com。

硬件

要完整地运行本项目，需要准备以下硬件：

1. reco WIFI插座 * n
2. 蓝牙4.0适配器 * 2
3. ibeacon模块   * n
4. 蓝牙音箱      * 1
5. 红外模块      * 1
6. zigbee传感器  * 2

#### reco WIFI插座

淘宝大概99一个，体积略大，好在控制协议是开放的，可以很方便地整合进LEHome。

买回来后，用reco的手机客户端配置一下插座使其正常工作，然后打开路由器的管理页面，将插座的ip记下来备用。

你也可以通过更改SwitchHelper.py使系统兼容自己的wifi插座。

#### 蓝牙4.0适配器

由于要使用ibeacon进行室内定位，故需要4.0以上的BT适配器。需要两个是因为一个负责连蓝牙音箱，一个负责接受ibeacon数据包。如果直接使用音频线来连音箱，则只需一个适配器即可

#### 蓝牙音箱

可以用普通音箱代替 :)

#### 红外模块

淘宝有售，选择一个开源控制协议的即可。为了避免广告嫌疑，这里不提供链接，有需要的可以私下联系。

#### zigbee传感器

淘宝有许多zigbee开发板出售，选择其中之一即可。为了避免广告嫌疑，这里不提供链接，有需要的可以私下联系。

注：要根据实际采用的红外模块和zigbee传感器模块来调整LEHome的源码（RILHelper.py和sensor_server.py）。


系统功能
========

本系统最大的特点是能支持简单的命令编程。

你可以输入：

    打开电灯

可以输入：

    打开电灯然后打开风扇

可以更复杂一点：

    循环每工作日晚上7点30分内容是打开风扇然后打开电灯

或者更更复杂一点：

	循环每工作日晚上7点30分内容是如果我在家里那么延时10分钟打开电灯然后如果当前温度大于数值26那么打开风扇然后播放语音#你好#


#### 如何查看系统支持的命令

打开usr/init.json，可以看到在"command"项下，有许多预定义的命令。

系统检测到命令词出现的时候，会调用相应的callback，所有业务逻辑都在callback里面完成。

#### 命令格式

命令由基本命令和控制语句组成。准许以下规则：

1. 基本命令 = delay + action + target + message
2. 基本命令 = 基本命令 + 控制语句
3. 命令 = trigger + 基本命令 + finish/stop

例如：

    打开风扇 -- 打开[action]风扇[target]
    延时10分钟打开电灯 -- 延时10分钟[delay]打开[action]电灯[target]
    查询公交车8路 -- 查询[action]公交车[target]8路[message]
    如果我在家里那么打开电灯 -- 如果[控制语句if]我在家里[基本命令]那么[控制语句then]打开电灯[基本命令]

以上命令不能直接被系统识别，需要用trigger和finish/stop包围

例如：

    你好打开风扇谢谢 -- 你好[trigger]打开[action]风扇[target]谢谢[finish]

*添加trigger和finish的原因是系统支持连续语音识别命令，需要考虑断句的情况，所以要添加两个标志位来截取命令。

#### 命令callback

所有命令对应的callback.py都保存在usr/callbacks/目录下。

在init.json文件中，可以通过：

    "callback":{
        "whiles":{
            "循环":"whiles.while_callback",
            "重复":"whiles.while_callback"
        },
    ...
	}

这样来指定。

callback主要如下所示：

    from lib.model import Callback
    
        class timer_callback(Callback.Callback):
        def callback(self, cmd, action, target, msg):
            ...

当命令词被触发时，相应callback的callback()方法会被调用，传入的参数由callback函数的定义决定。

联系方式
========

本项目断断续续做了一年，代码风格，逻辑实现等比较幼稚，加上本README写得极简，基本不可作为开发参考使用，故如有任何疑问，可联系legendmohe@foxmail.com。

