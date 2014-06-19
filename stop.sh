#!/bin/bash

echo 'kill home.py...'
ps -ef | awk '/python home\.py/ {print $2}' | xargs kill

# echo 'kill cmd_http_proxy.py...'
# ps -ef | awk '/python cmd_http_proxy\.py/ {print $2}' | xargs kill

echo 'kill sensor_server.py...'
ps -ef | awk '/python sensor_server\.py/ {print $2}' | xargs kill

s2t_pid=`ps -ef | awk '/python s2t_server\.py/ {print $2}'`
if [[ "$s2t_pid" ]]
then
    echo 'kill s2t_server.py...'
    kill -9 $s2t_pid
fi

echo 'LEHome stopped.'
