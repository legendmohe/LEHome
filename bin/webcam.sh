#!/bin/bash

DATE=$(date +"%Y-%m-%d_%H%M")

fswebcam -d /dev/video1 -r 1280x720 --no-banner /home/ubuntu/dev/LEHome/data/capture/$DATE.jpg
