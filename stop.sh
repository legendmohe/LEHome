#!/bin/bash

echo 'kill home.py...'
ps -ef | awk '/python home\.py/ {print $2}' | xargs kill

echo 'kill audio_server.py...'
ps -ef | awk '/sudo python audio_server\.py/ {print $2}' | sudo xargs kill

echo 'kill sensor_server.py...'
ps -ef | awk '/python sensor_server\.py/ {print $2}' | xargs kill

echo 'kill qqfm.py...'
ps -ef | awk '/sudo python qqfm.py/ {print $2}' | sudo xargs kill

s2t_pid=`ps -ef | awk '/python s2t_server\.py/ {print $2}'`
if [[ "$s2t_pid" ]]
then
    echo 'sudo kill s2t_server.py...'
    kill -9 $s2t_pid
fi

echo 'LEHome stopped.'
