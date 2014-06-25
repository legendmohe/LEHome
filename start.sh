#!/bin/bash

echo 'running home.py...'
python home.py > log/home.log 2>&1 &
rc=$?
if [[ $rc != 0 ]] ; then
    exit $rc
fi

# echo 'running cmd_http_proxy.py...'
# python cmd_http_proxy.py > log/cmd_http_proxy.log 2>&1 &
# rc=$?
# if [[ $rc != 0 ]] ; then
#     exit $rc
# fi

echo 'running audio server.py...'
sudo python audio_server.py > /dev/null 2>&1 &
rc=$?
if [[ $rc != 0 ]] ; then
    exit $rc
fi

echo 'running sensor_server.py...'
# python sensor_server.py > log/sensor.log 2>&1 &
python sensor_server.py > /dev/null 2>&1 &
rc=$?
if [[ $rc != 0 ]] ; then
    exit $rc
fi


if [[ $1 == "s2t" ]]
then
    echo 'running s2t_server.py...'
    sudo python s2t_server.py > log/s2t.log 2>&1 &
    rc=$?
    if [[ $rc != 0 ]] ; then
        exit $rc
    fi
fi

echo 'LEHome started.'
