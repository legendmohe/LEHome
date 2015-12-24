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
import os.path

from PIL import Image

from util.log import *
from util.Util import mkdir_p

class CameraHelper(object):

    def __init__(self):
        pass

    def _get_thumbnail_file_name(save_path, file_name):
        temp = file_name.rsplit(".", 1)
        thumbnail_name = temp[0] + ".thumbnail." + temp[1]
        return thumbnail_name

    def _get_opt_file_name(save_path, file_name):
        temp = file_name.rsplit(".", 1)
        opt_filename = temp[0] + ".opt." + temp[1]
        return opt_filename

# fswebcam -d /dev/video1 -r 1280x720 --no-banner /home/ubuntu/dev/LEHome/data/capture/$DATE.jpg
    def take_a_photo(self, save_path, file_name=None):
        if save_path is None or len(save_path) == 0:
            ERROR("save path is invaild")
            return None

        mkdir_p(save_path)
        if not save_path.endswith("/"):
            save_path += "/"
        if file_name is None or len(file_name) == 0:
            file_name = time.strftime("%Y_%m_%d_%H%M%S") + ".jpg"

        file_path = save_path + file_name
        INFO("taking photo...")
        subprocess.call([
            "fswebcam",
            # "-d", "/dev/video0",
            "-r", "1280*720",
            # "--no-banner",
            file_path
            ])
        # subprocess.call([
        #     "wget",
        #     "-O",
        #     file_path,
        #     "http://192.168.1.100:8080/?action=snapshot"
        #     ])
        if not os.path.isfile(file_path) :
            INFO("snapshot faild. no such file:" + file_path)
            return None, None
        INFO("save orginal photo:" + file_name)

        size = 320, 240
        t_name = self._get_thumbnail_file_name(file_name)
        im = Image.open(file_path)
        im.thumbnail(size, Image.ANTIALIAS)
        im.save(save_path + t_name, "JPEG")
        INFO("save thumbnail photo:" + t_name)
        return file_name, t_name


if __name__ == "__main__":
    import os
    os.chdir("/home/ubuntu/dev/LEHome/")
    CameraHelper().take_a_photo(
            save_path="/home/ubuntu/dev/LEHome/data/capture/"
            )
