#!/bin/bash

# echo 'kill remote_server_proxy.py...' ps -ef | awk '/python remote_server_proxy\.py/ {print $2}' | xargs kill -9

echo 'kill mqtt_server_proxy.py...'
ps -ef | awk '/python mqtt_server_proxy\.py/ {print $2}' | xargs kill -9

echo 'kill geo_fencing_server.py'
ps -ef | awk '/python geo_fencing_server\.py/ {print $2}' | xargs kill -9

echo 'kill remote_info_sender.py...'
ps -ef | awk '/python remote_info_sender\.py/ {print $2}' | xargs kill -9

echo 'kill home.py...'
ps -ef | awk '/python home\.py/ {print $2}' | xargs kill -9

echo 'kill audio_server.py...'
ps -ef | awk '/sudo python audio_server\.py/ {print $2}' | sudo xargs kill -INT

echo 'kill tag_endpoint.py'
ps -ef | awk '/python tag_endpoint\.py/ {print $2}' | xargs kill -9

echo 'kill qqfm.py...'
ps -ef | awk '/sudo python qqfm\.py/ {print $2}' | sudo xargs kill -INT

echo 'kill quick_button.py'
ps -ef | awk '/python quick_button\.py/ {print $2}' | sudo xargs kill -9

s2t_pid=`ps -ef | awk '/python s2t_server\.py/ {print $2}'`
if [[ "$s2t_pid" ]]
then
    echo 'kill s2t_server.py...'
    kill -9 $s2t_pid
fi

echo 'LEHome stopped.'
