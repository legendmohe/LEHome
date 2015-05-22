#!/usr/bin/env python
# encoding: utf-8

# Copyright 2010 Xinyu, He <legendmohe@foxmail.com>
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import subprocess
import time

from util.log import *

class CameraHelper(object):

    def __init__(self):
        pass

# fswebcam -d /dev/video1 -r 1280x720 --no-banner /home/ubuntu/dev/LEHome/data/capture/$DATE.jpg
    def take_a_photo(self, save_path, file_name=None):
        if save_path is None or len(save_path) == 0:
            ERROR("save path is invaild")
            return None

        if not save_path.endswith("/"):
            save_path += "/"
        if file_name is None or len(file_name) == 0:
            file_name = time.strftime("%Y_%m_%d_%H%M%S") + ".jpg"

        INFO("taking photo...")
        # subprocess.call([
        #     "fswebcam",
        #     "-d", "/dev/video1",
        #     "-r", "1280*720",
        #     "--no-banner",
        #     save_path + file_name
        #     ])
        subprocess.call([
            "wget",
            "-O",
            save_path + file_name,
            "http://192.168.1.112:8080/?action=snapshot"
            ])
        INFO("save photo:" + file_name)
        return file_name


if __name__ == "__main__":
    import os
    os.chdir("/home/ubuntu/dev/LEHome/")
    CameraHelper().take_a_photo(
            save_path="/home/ubuntu/dev/LEHome/data/capture/"
            )
