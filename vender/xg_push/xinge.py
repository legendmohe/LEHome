#!/usr/bin/env python
#-*- coding: utf-8 -*-
'''

Copyright ? 1998 - 2013 Tencent. All Rights Reserved. 腾讯公司 版权所有

'''

import json
import httplib
import urllib
import hashlib
import time

ERR_OK = 0
ERR_PARAM = -1
ERR_TIMESTAMP = -2
ERR_SIGN = -3
ERR_INTERNAL = -4
ERR_HTTP = -100
ERR_RETURN_DATA = -101

class TimeInterval(object):
    STR_START = 'start'
    STR_END = 'end'
    STR_HOUR = 'hour'
    STR_MIN = 'min'
    
    def __init__(self, startHour=0, startMin=0, endHour=0, endMin=0):
        self.startHour = startHour
        self.startMin = startMin
        self.endHour = endHour
        self.endMin = endMin
        
    def _isValidTime(self, hour, minute):
        return isinstance(hour, int) and isinstance(minute, int) and hour >= 0 and hour <=23 and minute >=0 and minute <= 59
    
    def _isValidInterval(self):
        return self.endHour * 60 + self.endMin >= self.startHour * 60 + self.startMin
        
    def GetObject(self):
        if not (self._isValidTime(self.startHour, self.startMin) and self._isValidTime(self.endHour, self.endMin)):
            return None
        if not self._isValidInterval():
            return None
        return {
                self.STR_START:{self.STR_HOUR:str(self.startHour), self.STR_MIN:str(self.startMin)},
                self.STR_END:{self.STR_HOUR:str(self.endHour), self.STR_MIN:str(self.endMin)}
            }

class ClickAction(object):
    TYPE_ACTIVITY = 1
    TYPE_URL = 2
    TYPE_INTENT = 3
    TYPE_PACKAGE = 4
    
    def __init__(self, actionType=1, url='', confirmOnUrl=0, activity='', intent=''):
        self.actionType = actionType
        self.url = url
        self.confirmOnUrl = confirmOnUrl
        self.activity = activity
        self.intent = intent
        self.intentFlag = 0
        self.pendingFlag = 0
        self.packageName = ""
        self.packageDownloadUrl = ""
        self.confirmOnPackage = 1
        
    def GetObject(self):
        ret = {}
        ret['action_type'] = self.actionType
        if self.TYPE_ACTIVITY == self.actionType:
            ret['activity'] = self.activity
            ret['aty_attr'] = {'if':self.intentFlag, 'pf':self.pendingFlag}
        elif self.TYPE_URL == self.actionType:
            ret['browser'] = {'url':self.url, 'confirm':self.confirmOnUrl}
        elif self.TYPE_INTENT == self.actionType:
            ret['intent'] = self.intent
        elif self.TYPE_PACKAGE == self.actionType:
            ret['package_name'] = {'packageDownloadUrl':self.packageDownloadUrl, 'confirm':self.confirmOnPackage, 'packageName':self.packageName}
        
        return ret

class Style(object):
    N_INDEPENDENT = 0
    N_THIS_ONLY = -1

    def __init__(self, builderId=0, ring=0, vibrate=0, clearable=1, nId=N_INDEPENDENT):
        self.builderId = builderId
        self.ring = ring
        self.vibrate = vibrate
        self.clearable = clearable
        self.nId = nId
        self.ringRaw = ""
        self.lights = 1
        self.iconType = 0
        self.iconRes = ""
        self.styleId = 1
        self.smallIcon = ""

class Message(object):
    TYPE_NOTIFICATION = 1
    TYPE_MESSAGE = 2
    
    PUSH_SINGLE_PKG = 0
    PUSH_ACCESS_ID = 1
    
    def __init__(self):
        self.title = ""
        self.content = ""
        self.expireTime = 0
        self.sendTime = ""
        self.acceptTime = ()
        self.type = 0
        self.style = None
        self.action = None
        self.custom = {}
        self.multiPkg = self.PUSH_SINGLE_PKG
        self.raw = None
        self.loopTimes = 0
        self.loopInterval = 0
        
    def GetMessageObject(self):
        if self.raw is not None:
            if isinstance(self.raw, basestring):
                return json.loads(self.raw)
            else:
                return self.raw
        
        message = {}
        message['title'] = self.title
        message['content'] = self.content
        
        # TODO: check custom
        message['custom_content'] = self.custom
        
        acceptTimeObj = self.GetAcceptTimeObject()
        if None == acceptTimeObj:
            return None
        elif acceptTimeObj != []:
            message['accept_time'] = acceptTimeObj
        
        if self.type == self.TYPE_NOTIFICATION:
            if None == self.style:
                style = Style()
            else:
                style = self.style
                
            if isinstance(style, Style):
                message['builder_id'] = style.builderId
                message['ring'] = style.ring
                message['vibrate'] = style.vibrate
                message['clearable'] = style.clearable
                message['n_id'] = style.nId
                message['ring_raw'] = style.ringRaw
                message['lights'] = style.lights
                message['icon_type'] = style.iconType
                message['icon_res'] = style.iconRes
                message['style_id'] = style.styleId
                message['small_icon'] = style.smallIcon
            else:
                # style error
                return None
            
            if None == self.action:
                action = ClickAction()
            else:
                action = self.action
            
            if isinstance(action, ClickAction):
                message['action'] = action.GetObject()
            else:
                # action error
                return None
        elif self.type == self.TYPE_MESSAGE:
            pass
        else:
            return None
        
        return message
    
    def GetAcceptTimeObject(self):
        ret = []
        for ti in self.acceptTime:
            if isinstance(ti, TimeInterval):
                o = ti.GetObject()
                if o is None:
                    return None
                else:
                    ret.append(ti.GetObject())
            else:
                return None
        return ret
        
class MessageIOS(Message):
    def __init__(self):
        Message.__init__(self)
        self.alert = None
        self.badge = None
        self.sound = None
        self.category = None
        self.raw = None
        
    def GetMessageObject(self):
        if self.raw is not None:
            if isinstance(self.raw, basestring):
                return json.loads(self.raw)
            else:
                return self.raw
            
        message = self.custom
        
        acceptTimeObj = self.GetAcceptTimeObject()
        if None == acceptTimeObj:
            return None
        elif acceptTimeObj != []:
            message['accept_time'] = acceptTimeObj
            
        aps = {}
        if isinstance(self.alert, basestring) or isinstance(self.alert, dict):
            aps['alert'] = self.alert
        else:
            # alert type error
            return None
        if self.badge is not None:
            aps['badge'] = self.badge
        if self.sound is not None:
            aps['sound'] = self.sound
        if self.category is not None:
            aps['category'] = self.category
        message['aps'] = aps
        return message

class MessageStatus(object):
    def __init__(self, status, startTime):
        self.status = status
        self.startTime = startTime
    
    def __str__(self):
        return str(vars(self))
    
    def __repr__(self):
        return self.__str__()
        
class TagTokenPair(object):
    def __init__(self, tag, token):
        self.tag = str(tag)
        self.token = str(token)

class XingeApp(object):
    DEVICE_ALL = 0
    DEVICE_BROWSER = 1
    DEVICE_PC = 2
    DEVICE_ANDROID = 3
    DEVICE_IOS = 4
    DEVICE_WP = 5
    
    PATH_PUSH_TOKEN = '/v2/push/single_device'
    PATH_PUSH_ACCOUNT = '/v2/push/single_account'
    PATH_PUSH_ACCOUNT_LIST = '/v2/push/account_list'
    PATH_PUSH_ALL = '/v2/push/all_device'
    PATH_PUSH_TAGS = '/v2/push/tags_device'
    PATH_GET_PUSH_STATUS = '/v2/push/get_msg_status'
    PATH_GET_DEV_NUM = '/v2/application/get_app_device_num'
    PATH_QUERY_TAGS = '/v2/tags/query_app_tags'
    PATH_CANCEL_TIMING_PUSH = '/v2/push/cancel_timing_task'
    PATH_BATCH_SET_TAG = '/v2/tags/batch_set'
    PATH_BATCH_DEL_TAG = '/v2/tags/batch_del'
    PATH_QUERY_TOKEN_TAGS = '/v2/tags/query_token_tags'
    PATH_QUERY_TAG_TOKEN_NUM = '/v2/tags/query_tag_token_num'
    
    ENV_PROD = 1
    ENV_DEV = 2
    
    def __init__(self, accessId, secretKey):
        self.accessId = int(accessId)
        self.secretKey = str(secretKey)

    def ValidateToken(self, token):
        if(self.accessId >= 2200000000):
            return len(token) == 64
        else:
            return (len(token) == 40 or len(token) == 64)
        
    def InitParams(self):
        params = {}
        params['access_id'] = self.accessId
        params['timestamp'] = XingeHelper.GenTimestamp()
        return params
    
    def SetPushParams(self, params, message, environment):
        params['expire_time'] = message.expireTime
        params['send_time'] = message.sendTime
        params['message_type'] = message.type
        params['multi_pkg'] = message.multiPkg
        params['environment'] = environment
        msgObj = message.GetMessageObject()
        if None == msgObj:
            return False
        else:
            params['message'] = json.dumps(msgObj, separators=(',',':'), ensure_ascii=False)
            return True
        
    def Request(self, path, params):
        params['sign'] = XingeHelper.GenSign(path, params, self.secretKey)
        return XingeHelper.Request(path, params)
    
    def PushSingleDevice(self, deviceToken, message, environment=0):
        deviceToken = str(deviceToken)
        if not (isinstance(message, Message) or isinstance(message, MessageIOS)):
            return ERR_PARAM, 'message type error'
        
        params = self.InitParams()
        if False == self.SetPushParams(params, message, environment):
            return ERR_PARAM, 'invalid message, check your input'
        params['device_token'] = deviceToken
        
        ret = self.Request(self.PATH_PUSH_TOKEN, params)
        return ret[0], ret[1]
    
    def PushSingleAccount(self, deviceType, account, message, environment=0):
        deviceType = int(deviceType)
        account = str(account)
        if not isinstance(message, Message):
            return ERR_PARAM, 'message type error'
        
        params = self.InitParams()
        if False == self.SetPushParams(params, message, environment):
            return ERR_PARAM, 'invalid message, check your input'
        params['device_type'] = deviceType
        params['account'] = account
        
        ret = self.Request(self.PATH_PUSH_ACCOUNT, params)
        return ret[0], ret[1]
    
    def PushAccountList(self, deviceType, accountList, message, environment=0):
        deviceType = int(deviceType)
        if not isinstance(message, Message):
            return ERR_PARAM, 'message type error'
        if not isinstance(accountList, (tuple, list)):
            return ERR_PARAM, 'accountList type error', None
        
        params = self.InitParams()
        if False == self.SetPushParams(params, message, environment):
            return ERR_PARAM, 'invalid message, check your input'
        params['device_type'] = deviceType
        params['account_list'] = json.dumps(accountList)
        params['send_time'] = ""
        
        ret = self.Request(self.PATH_PUSH_ACCOUNT_LIST, params)
        return ret[0], ret[1], ret[2]
    
    def PushAllDevices(self, deviceType, message, environment=0):
        deviceType = int(deviceType)
        if not (isinstance(message, Message) or isinstance(message, MessageIOS)):
            return ERR_PARAM, 'message type error', None
        
        params = self.InitParams()
        if False == self.SetPushParams(params, message, environment):
            return ERR_PARAM, 'invalid message, check your input', None
        params['device_type'] = deviceType
        params['loop_times'] = message.loopTimes
        params['loop_interval'] = message.loopInterval
        
        ret = self.Request(self.PATH_PUSH_ALL, params)
        result = None
        if ERR_OK == ret[0]:
            if 'push_id' not in ret[2]:
                return ERR_RETURN_DATA, '', result
            else:
                result = ret[2]['push_id']
        return ret[0], ret[1], result
    
    def PushTags(self, deviceType, tagList, tagsOp, message, environment=0):
        deviceType = int(deviceType)
        if not (isinstance(message, Message) or isinstance(message, MessageIOS)):
            return ERR_PARAM, 'message type error', None
        if not isinstance(tagList, (tuple, list)):
            return ERR_PARAM, 'tagList type error', None
        if tagsOp not in ('AND','OR'):
            return ERR_PARAM, 'tagsOp error', None
        
        params = self.InitParams()
        if False == self.SetPushParams(params, message, environment):
            return ERR_PARAM, 'invalid message, check your input', None
        params['device_type'] = deviceType
        params['tags_list'] = json.dumps([str(tag) for tag in tagList], separators=(',',':'))
        params['tags_op'] = tagsOp
        params['loop_times'] = message.loopTimes
        params['loop_interval'] = message.loopInterval
        
        ret = self.Request(self.PATH_PUSH_TAGS, params)
        result = None
        if ERR_OK == ret[0]:
            if 'push_id' not in ret[2]:
                return ERR_RETURN_DATA, '', result
            else:
                result = ret[2]['push_id']
        return ret[0], ret[1], result
    
    def QueryPushStatus(self, pushIdList):
        if not isinstance(pushIdList, (tuple, list)):
            return ERR_PARAM, 'pushIdList type error', None
        
        params = self.InitParams()
        params['push_ids'] = json.dumps([{'push_id':str(pushId)} for pushId in pushIdList], separators=(',',':'))
        
        ret = self.Request(self.PATH_GET_PUSH_STATUS, params)
        result = {}
        if ERR_OK == ret[0]:
            if 'list' not in ret[2]:
                return ERR_RETURN_DATA, '', result
            for status in ret[2]['list']:
                result[status['push_id']] = MessageStatus(status['status'], status['start_time'])
            
        return ret[0], ret[1], result
    
    def QueryDeviceCount(self):
        params = self.InitParams()
        ret = self.Request(self.PATH_GET_DEV_NUM, params)
        result = None
        if ERR_OK == ret[0]:
            if 'device_num' not in ret[2]:
                return ERR_RETURN_DATA, '', result
            else:
                result = ret[2]['device_num']
        return ret[0], ret[1], result
    
    def QueryTags(self, start, limit):
        params = self.InitParams()
        params['start'] = int(start)
        params['limit'] = int(limit)
        
        ret = self.Request(self.PATH_QUERY_TAGS, params)
        retCode = ret[0]
        total = None
        tags = []
        if ERR_OK == ret[0]:
            if 'total' not in ret[2]:
                retCode = ERR_RETURN_DATA
            else:
                total = ret[2]['total']
                
            if 'tags' in ret[2]:
                tags = ret[2]['tags']
        return retCode, ret[1], total, tags
    
    def CancelTimingPush(self, pushId):
        params = self.InitParams()
        params['push_id'] = str(pushId)
        
        ret = self.Request(self.PATH_CANCEL_TIMING_PUSH, params)
        return ret[0], ret[1]
        
    def BatchSetTag(self, tagTokenPairs):
        for pair in tagTokenPairs:
            if not isinstance(pair, TagTokenPair):
                return ERR_PARAM, 'tag-token pair type error!'
            if False == self.ValidateToken(pair.token):
                return ERR_PARAM, ('invalid token %s' % pair.token)
        params = self.InitParams()
        params['tag_token_list'] = json.dumps([[pair.tag, pair.token] for pair in tagTokenPairs])
        
        ret = self.Request(self.PATH_BATCH_SET_TAG, params)
        return ret[0], ret[1]
        
    def BatchDelTag(self, tagTokenPairs):
        for pair in tagTokenPairs:
            if not isinstance(pair, TagTokenPair):
                return ERR_PARAM, 'tag-token pair type error!'
            if False == self.ValidateToken(pair.token):
                return ERR_PARAM, ('invalid token %s' % pair.token)
        params = self.InitParams()
        params['tag_token_list'] = json.dumps([[pair.tag, pair.token] for pair in tagTokenPairs])
        
        ret = self.Request(self.PATH_BATCH_DEL_TAG, params)
        return ret[0], ret[1]

    def QueryTokenTags(self, token):
        params = self.InitParams()
        params['device_token'] = str(token)

        ret = self.Request(self.PATH_QUERY_TOKEN_TAGS, params)
        result = None
        if 'tags' in ret[2]:
            result = ret[2]['tags']
        return ret[0], ret[1], result

    def QueryTagTokenNum(self, tag):
        params = self.InitParams()
        params['tag'] = str(tag)

        ret = self.Request(self.PATH_QUERY_TAG_TOKEN_NUM, params)
        result = None
        if 'device_num' in ret[2]:
            result = ret[2]['device_num']
        return ret[0], ret[1], result

class XingeHelper(object):
    XINGE_HOST = 'openapi.xg.qq.com'
    XINGE_PORT = 80
    TIMEOUT = 10
    HTTP_METHOD = 'POST'
    HTTP_HEADERS = {'HOST' : XINGE_HOST, 'Content-Type' : 'application/x-www-form-urlencoded'}
    
    STR_RET_CODE = 'ret_code'
    STR_ERR_MSG = 'err_msg'
    STR_RESULT = 'result'
    
    @classmethod
    def SetServer(cls, host=XINGE_HOST, port=XINGE_PORT):
        cls.XINGE_HOST = host
        cls.XINGE_PORT = port
        cls.HTTP_HEADERS['HOST'] = cls.XINGE_HOST
    
    @classmethod
    def GenSign(cls, path, params, secretKey):
        ks = sorted(params.keys())
        paramStr = ''.join([('%s=%s' % (k, params[k])) for k in ks])
        signSource = '%s%s%s%s%s' % (cls.HTTP_METHOD, cls.XINGE_HOST, path, paramStr, secretKey)
        return hashlib.md5(signSource).hexdigest()
    
    @classmethod
    def GenTimestamp(cls):
        return int(time.time())
    
    @classmethod
    def Request(cls, path, params):
        httpClient = httplib.HTTPConnection(cls.XINGE_HOST, cls.XINGE_PORT, timeout=cls.TIMEOUT)
        if cls.HTTP_METHOD == 'GET':
            httpClient.request(cls.HTTP_METHOD, ('%s?%s' % (path, urllib.urlencode(params))), headers=cls.HTTP_HEADERS)
        elif cls.HTTP_METHOD == 'POST':
            httpClient.request(cls.HTTP_METHOD, path, urllib.urlencode(params), headers=cls.HTTP_HEADERS)
        else:
            # invalid method
            return ERR_PARAM, '', None
        
        response = httpClient.getresponse()
        retCode = ERR_RETURN_DATA
        errMsg = ''
        result = {}
        if 200 != response.status:
            retCode = ERR_HTTP
        else:
            data = response.read()
            retDict = json.loads(data)
            if(cls.STR_RET_CODE in retDict):
                retCode = retDict[cls.STR_RET_CODE]
            if(cls.STR_ERR_MSG in retDict):
                errMsg = retDict[cls.STR_ERR_MSG]
            if(cls.STR_RESULT in retDict):
                if isinstance(retDict[cls.STR_RESULT], dict):
                    result = retDict[cls.STR_RESULT]
                elif isinstance(retDict[cls.STR_RESULT], list):
                    result = retDict[cls.STR_RESULT]
                elif retDict[cls.STR_RESULT] == '':
                    pass
                else:
                    retCode = ERR_RETURN_DATA
        return retCode, errMsg, result

def _BuildAndroidNotification(title, content):
    msg = Message()
    msg.type = Message.TYPE_NOTIFICATION
    msg.title = title
    msg.content = content
    msg.style = Style(1, 1)
    msg.action = ClickAction()
    return msg

def _BuildIosNotification(content):
    msg = MessageIOS()
    msg.alert = content
    return msg
            
def PushTokenAndroid(accessId, secretKey, title, content, token):
    x = XingeApp(accessId, secretKey)
    return x.PushSingleDevice(token, _BuildAndroidNotification(title, content))

def PushAccountAndroid(accessId, secretKey, title, content, account):
    x = XingeApp(accessId, secretKey)
    return x.PushSingleAccount(0, account, _BuildAndroidNotification(title, content))

def PushAllAndroid(accessId, secretKey, title, content):
    x = XingeApp(accessId, secretKey)
    return x.PushAllDevices(0, _BuildAndroidNotification(title, content))

def PushTagAndroid(accessId, secretKey, title, content, tag):
    x = XingeApp(accessId, secretKey)
    return x.PushTags(0, (tag,), 'OR', _BuildAndroidNotification(title, content))

def PushTokenIos(accessId, secretKey, content, token, env):
    x = XingeApp(accessId, secretKey)
    return x.PushSingleDevice(token, _BuildIosNotification(content), env)

def PushAccountIos(accessId, secretKey, content, account, env):
    x = XingeApp(accessId, secretKey)
    return x.PushSingleAccount(0, account, _BuildIosNotification(content), env)

def PushAllIos(accessId, secretKey, content, env):
    x = XingeApp(accessId, secretKey)
    return x.PushAllDevices(0, _BuildIosNotification(content), env)

def PushTagIos(accessId, secretKey, content, tag, env):
    x = XingeApp(accessId, secretKey)
    return x.PushTags(0, (tag,), 'OR', _BuildIosNotification(content), env)
