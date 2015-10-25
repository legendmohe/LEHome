#!/bin/bash

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd $DIR

echo 'running tag_endpoint.py'
python tag_endpoint.py > /dev/null 2>&1 &
rc=$?
if [[ $rc != 0 ]] ; then
    exit $rc
fi

echo 'running audio server.py...'
sudo python audio_server.py > /dev/null 2>&1 &
rc=$?
if [[ $rc != 0 ]] ; then
    exit $rc
fi

echo 'running home.py...'
python home.py > /dev/null 2>&1 &
rc=$?
if [[ $rc != 0 ]] ; then
    exit $rc
fi

# echo 'running remote server proxy.py'
# python remote_server_proxy.py > log/remote_server.log 2>&1 &
# rc=$?
# if [[ $rc != 0 ]] ; then
#     exit $rc
# fi

echo 'running mqtt server proxy.py'
python mqtt_server_proxy.py > log/mqtt_server.log 2>&1 &
rc=$?
if [[ $rc != 0 ]] ; then
    exit $rc
fi

if [[ $1 != "silent" ]]
then
    echo 'running remote info sender.py'
    python remote_info_sender.py > log/remote_proxy.log 2>&1 &
    rc=$?
    if [[ $rc != 0 ]] ; then
        exit $rc
    fi
fi
# echo 'running sensor_server.py...'
# # python sensor_server.py > log/sensor.log 2>&1 &
# python sensor_server.py > /dev/null 2>&1 &
# rc=$?
# if [[ $rc != 0 ]] ; then
#     exit $rc
# fi

echo 'running qqfm.py...'
cd ../qqfm/
sudo python qqfm.py > log/qqfm.log 2>&1 &
cd ../LEHome/
rc=$?
if [[ $rc != 0 ]] ; then
    exit $rc
fi

echo 'running quick_button.py'
sudo python quick_button.py > /dev/null 2>&1 &
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
