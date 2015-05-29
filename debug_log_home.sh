#!/bin/bash
tail -n 100 -f log/home_debug.log | grep "$@"
