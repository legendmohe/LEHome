#!/usr/bin/env python
#encoding='utf-8' 

import urllib
import urllib2
import json

g_conf = {
    "links":
    {
        "while" : ["action", "delay"],
        "if" : ["action", "delay"],
        "then" : ["if", "while", "action", "delay"],
        "else" : ["action", "delay"],
        "delay" : ["time", "action"],
        "trigger" : ["while", "if", "delay", "action"],
        "action" : ["target", "message", "next", "logical", "compare", "then", "finish"],
        "target" : ["message", "next", "logical", "compare", "then", "finish"],
        "finish" : ["trigger"],
        "next" : ["while", "if", "delay", "action"],
        "logical" : ["action", "delay"],
        "compare" : ["action", "delay"],
        "message" : ["next", "logical", "compare", "then", "finish"],
        "time" : ["action"]
    },
    "message_seq":"#",
    "time_seq":"#",
    "init_state":"trigger"
}



def get_conf_file(id):
    upload_url = "http://lehome.sinaapp.com/auto/init?id=%s" % id

    req = urllib2.Request(upload_url)
    print("get: %s" % upload_url)

    res_data = urllib2.urlopen(req)
    res = res_data.read()
    print(res)
    
def post_conf_file(id, data, version):
    if version is None:
        print("version is None!")
        return
    print("data:%s" % type(data))

    post_url = "http://lehome.sinaapp.com/auto/init?id=%s&v=%s" % (id, version)
    req = urllib2.Request(url=post_url, data=data)
    print(req)

    res_data = urllib2.urlopen(req)
    res = res_data.read()
    print(res)

def init_to_conf(conf_file_path):
    global g_conf

    with open(conf_file_path, 'r') as f:
        init_data = json.loads(f.read())

    g_conf['nodes'] = init_data['command']
    return json.dumps(g_conf)

def main(id, conf_file_path, version):
    if id is None:
        print("id is None!")
        return

    if not conf_file_path is None:
        conf_file_content = init_to_conf(conf_file_path)
        post_conf_file(id, conf_file_content, version)
    else:
        get_conf_file(id)
    

if __name__ == "__main__" :
    from argparse import ArgumentParser
    parser = ArgumentParser()

    parser.add_argument("-f", "--file",
                        dest="conf_file_path",
                        default=None,
                        help="conf file path",
                        metavar="FILE")
    parser.add_argument("-i", "--id",
                        dest="id",
                        default=None,
                        help="id number")
    parser.add_argument("-v", "--version",
                        dest="version",
                        default=None,
                        help="version number")

    args = parser.parse_args()

    print("id:%s conf_file_path:%s version:%s" % (
        id,
        args.conf_file_path,
        args.version
        ))
    main(args.id, args.conf_file_path, args.version)
