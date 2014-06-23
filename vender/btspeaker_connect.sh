#!/bin/bash

# bluez-test-audio connect A0:E9:DB:04:42:D7

pid=0
address="A0:E9:DB:04:42:D7"
con_started=false
while (sleep 5)
do
    if [[ $con_started == false ]] ; then
        connected=$(hcitool con) > /dev/null
        if [[ $connected =~ .*${address}.* ]] ; then
            bluez-test-audio connect A0:E9:DB:04:42:D7
            echo $! > /tmp/btspeaker_connect.pid
            con_started=true
            echo $address connected started btspeaker
        fi
    fi

    if [[ $con_started == true ]] ; then
        connected=$(hcitool con) > /dev/null
        if [[ ! $connected =~ .*${address}.* ]] ; then
            pid=$(cat /tmp/btspeaker_connect.pid)
            kill -9 $pid
            rm /tmp/btspeaker_connect.pid
            con_started=false
            echo $address disconnected stopped btspeaker
        fi
    fi
done
