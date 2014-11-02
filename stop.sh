#!/bin/bash

echo 'kill home.py...'
ps -ef | awk '/python home\.py/ {print $2}' | xargs kill -INT

echo 'kill audio_server.py...'
ps -ef | awk '/sudo python audio_server\.py/ {print $2}' | sudo xargs kill -INT

# echo 'kill sensor_server.py...'
# ps -ef | awk '/python sensor_server\.py/ {print $2}' | xargs kill
#
echo 'kill tag_endpoint.py'
ps -ef | awk '/python tag_endpoint\.py/ {print $2}' | xargs kill -INT

echo 'kill qqfm.py...'
ps -ef | awk '/sudo python qqfm\.py/ {print $2}' | sudo xargs kill -INT

s2t_pid=`ps -ef | awk '/sudo python s2t_server\.py/ {print $2}'`
if [[ "$s2t_pid" ]]
then
    echo 'sudo kill s2t_server.py...'
    sudo kill -9 $s2t_pid
fi

echo 'LEHome stopped.'
