#!/bin/bash
DEBUG_LOG_PATH="/run/shm/lehome"
if [ -d $DEBUG_LOG_PATH ]; then
    tail -n 100 -f $DEBUG_LOG_PATH/log/home_debug.log | grep "$@"
else
    tail -n 100 -f log/home_debug.log | grep "$@"
fi
