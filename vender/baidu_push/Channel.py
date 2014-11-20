#!/usr/bin/python
# _*_ coding: UTF-8 _*_

import time

import urllib

import hashlib

import json

from lib.ChannelException import ChannelException

from lib.RequestCore import *


###
# 百度云推送PUSH服务 Python SDK
#
# 本文件提供百度云推动PUSH的Python版本SDK
#
# @author 百度云平台部
# @copyright Copyright (c) 2012-2020 百度在线网络技术(北京)有限公司
# @version 1.0.0
### 



class Channel(object):
	'''Channel类提供百度云PUSH服务的Python版本SDK，
	用户首先实例化这个类，
	设置自己的apiKey,和 secretKey，即可使用PUSH服务接口
	'''
	#发起请求时的时间戳
	TIMESTAMP = 'timestamp'

	#请求过期的时间, 默认为10分钟
	EXPIRES = 'expires'

	#API版本号
	VERSION = 'v'

	#消息通道ID号
	CHANNEL_ID = 'channel_id'

	#用户类型	
	USER_ID = 'user_id'

	#用户ID的类型
	USER_TYPE = 'user_type'

	#设备类型
	DEVICE_TYPE = 'device_type'

	#第几页，批量查询是，需要指定start, 默认为0
	START = 'start'

	#每页多少条记录，默认为100
	LIMIT = 'limit'
	
	#消息
	MESSAGES = 'messages'
	
	#消息id
	MSG_IDS = 'msg_ids'

	#消息key，可以按key去除重复消息
	MSG_KEYS = 'msg_keys'

	#消息类型，0：消息（透传）， 1：通知， 默认为0	
	MESSAGE_TYPE = 'message_type'

	#消息过期时间，默认86400秒
	MESSAGE_EXPIRES = 'message_expires'

	#消息标签名，可按标签分组
	TAG_NAME = 'tag'

	#消息标签扩展信息
	TAG_INFO = 'info'

	#消息标签id
	TAG_ID = 'tid'
	
	#应用id，从百度开发者中心获得
	APPID = 'appid'

	#应用key，从百度开发者中心获得,是创建Channel的必须参数
	API_KEY = 'apikey'

	#从百度开发者中心获得，是创建Channel的必须参数
	SECRET_KEY = 'secret_key'

	#Channel常量，用户不必关注	
	SIGN = 'sign'
	METHOD = 'method'
	HOST = 'host'
	PRODUCT = 'channel'
	DEFAULT_HOST = 'channel.api.duapp.com'
#	DEFAULT_HOST = 'localhost:1234' #'channel.api.duapp.com'

	#证书相关常量
	NAME = 'name'
	DESCRIPTION = 'description'
	CERT = 'cert'
	RELEASE_CERT = 'release_cert'
	DEV_CERT = 'dev_cert'

	#推送类型
	PUSH_TYPE = 'push_type'

	#可选推送类型
	PUSH_TO_USER = 1
	PUSH_TO_TAG = 2
	PUSH_TO_ALL = 3

	#Channel 错误常量
	CHANNEL_SDK_SYS = 1
	CHANNEL_SDK_INIT_FAIL = 2
	CHANNEL_SDK_PARAM = 3
	CHANNEL_SDK_HTTP_STATUS_ERROR_AND_RESULT_ERROR = 4
	CHANNEL_SDK_HTTP_STATUS_OK_BUT_RESULT_ERROR = 5
		
	###
	# 对外接口
	###
	
	def __init__(self, apiKey, secretKey, arr_curlOpts = None):
		self._apiKey = apiKey
		self._secretKey = secretKey
		self._requestId = 0
		if arr_curlOpts is None:
			self._curlOpts = dict(IMEOUT = 30, CONNECTTIMEOUT = 5)
		else:
			self._curlOpts = arr_curlOpts
		self._arrayErrorMap = {
			'0' : 'python sdk error',
			Channel.CHANNEL_SDK_SYS : 'php sdk error',
			Channel.CHANNEL_SDK_INIT_FAIL : 'php sdk init error', 
			Channel.CHANNEL_SDK_PARAM : 'lack param',
			Channel.CHANNEL_SDK_HTTP_STATUS_ERROR_AND_RESULT_ERROR : 
				'http status is error, and the body returned is not a json string',
			Channel.CHANNEL_SDK_HTTP_STATUS_OK_BUT_RESULT_ERROR :
				 'http status is ok, but the body returned is not a json string'}
		self._method_channel_in_body = [
			'push_msg', 'set_tag', 'fetch_tag', 
			'delete_tag', 'query_user_tags']
		if(not isinstance(self._curlOpts, dict)):
			raise ChannelExcepthion(
				'invalid param -arr_curlopt is not an dict', 
				Channel.CHANNEL_SDK_INIT_FAIL) 


	def setApiKey(self, apiKey):
		self._apiKey = apiKey


	def setSecretKey(self, secretKey):
		self._secretKey = secretKey


	def getRequestId(self):
		return self._requestId


	# 服务器端根据userId, 查询绑定信息
	# 用户关注：是
	def queryBindList(self, userId, optional = None):
		"""
		服务器端根据userId, 查询绑定信息
		参数：
			str userId:  用户ID号
			dict optional: 可选参数 
		返回值：
			成功:python字典； 失败：False
		"""
		try:
			tmpArgs = [userId, optional]
			arrArgs = self._mergeArgs([Channel.USER_ID], tmpArgs)	
			arrArgs[Channel.METHOD] = 'query_bindlist'
			return self._commonProcess(arrArgs)
		except ChannelException, e:
			self._channelExceptionHandler(e)	
			return False
			

	# 推送消息
	# 用户关注：是
	def pushMessage(self, push_type, messages, 
			message_keys, optional = None):
		"""
		推送消息
		参数:
			push_type: 推送消息的类型
			messages：消息内容
			message_keys: 消息key
			optional: 可选参数
		返回值 成功：python字典; 失败：False
		"""
		try:
			tmpArgs = [push_type, messages, message_keys, optional]
			arrArgs = self._mergeArgs([Channel.PUSH_TYPE, Channel.MESSAGES,
						 Channel.MSG_KEYS], tmpArgs)
			arrArgs[Channel.METHOD] = 'push_msg'
			if(push_type == Channel.PUSH_TO_USER):
				if(not arrArgs.has_key(Channel.USER_ID) or 
					arrArgs[Channel.USER_ID] is None):
					raise ChannelException("userId should be specified in optional when pushType is PUSH_TO_USER", self.CHANNEL_SDK_PARAM)
			elif(push_type == Channel.PUSH_TO_TAG):
				if(not arrArgs.has_key(Channel.TAG_NAME) or 
					arrArgs[Channel.TAG_NAME] is None):
					raise ChannelException("tagName should be specified in optional when pushType is PUSH_TO_TAG", self.CHANNEL_SDK_PARAM)
			elif(push_type == Channel.PUSH_TO_ALL):
				pass
			else:
				raise ChannelException("pushType value is invalid", self.CHANNEL_SDK_PARAM)
			
			arrArgs[Channel.PUSH_TYPE] = push_type
			if(isinstance(arrArgs[Channel.MESSAGES], list)):
				arrArgs[Channel.MESSAGES] = json.dumps(arrArgs[Channel.MESSAGES])
			if(isinstance(arrArgs[Channel.MSG_KEYS], list)):
				arrArgs[Channel.MSG_KEYS] = json.dumps(arrArgs[Channel.MSG_KEYS])
			return self._commonProcess(arrArgs)

		except ChannelException, e:
			self._channelExceptionHandler(e)
			return False


	#校验userId是否已经绑定
	#用户关注：是
	def verifyBind(self, userId, optional = None):
		"""
		校验userId是否已经绑定
		参数：
			userId:用户id
			optional:可选参数
		返回值：
			成功：python数组；失败False
		"""
		try:
			tmpArgs = [userId, optional]
			arrArgs = self._mergeArgs([Channel.USER_ID], tmpArgs)
			arrArgs[Channel.METHOD] = 'verify_bind';
			return self._commonProcess(arrArgs)
		except ChannelException, e:
			self._channelExceptionHandler(e)
			return False

	
	#根据userId查询消息
	#用户关注：是
	def fetchMessage(self, userId, optional = None):
		"""
		根据userId查询消息
		参数：
			userId:用户id
			optional:可选参数
		返回值：
			成功：python字典； 失败：False
		"""
		try:
			tmpArgs = [userId, optional]
			arrArgs = self._mergeArgs([Channel.USER_ID], tmpArgs)
			arrArgs[Channel.METHOD] = 'fetch_msg';
			return self._commonProcess(arrArgs)
		except ChannelException, e:
			self._channelExceptionHandler(e)
			return False

	#根据userId查询消息个数
	#用户关注：是
	def fetchMessageCount(self, userId, optional = None):
		"""
		根据userId查询消息个数
		参数：
			userId:用户id
			optional:可选参数
		返回值：
			成功：python字典； 失败：False
		"""
		try:
			tmpArgs = [userId, optional]
			arrArgs = self._mergeArgs([Channel.USER_ID], tmpArgs)
			arrArgs[Channel.METHOD] = 'fetch_msgcount';
			return self._commonProcess(arrArgs)
		except ChannelException, e:
			self._channelExceptionHandler(e)
			return False


	#根据userId, msgIds删除消息
	#用户关注：是
	def deleteMessage(self, userId, msgId, optional = None):
		"""
		根据userId, msgIds删除消息
		参数：
			userId:用户id
			msgIds:消息id
			optional:可选参数
		返回值：
			成功：python字典； 失败：False
		"""
		try:
			tmpArgs = [userId, msgId, optional]
			arrArgs = self._mergeArgs([Channel.USER_ID, Channel.MSG_IDS], tmpArgs)
			arrArgs[Channel.METHOD] = 'delete_msg';
			if(isinstance(arrArgs[Channel.MSG_IDS], list)):
				arrArgs[Channel.MSG_IDS] = json.dumps(arrArgs[Channel.MSG_IDS])
			return self._commonProcess(arrArgs)
		except ChannelException, e:
			self._channelExceptionHandler(e)


	#设置消息标签
	#用户关注：是
	def setTag(self, tagName, optional = None):
		"""
		设置消息标签
		参数：
			tagName:标签
			optional:可选参数
		返回值：
			成功：python字典； 失败：False
		"""
		try:
			tmpArgs = [tagName, optional]
			arrArgs = self._mergeArgs([Channel.TAG_NAME], tmpArgs)
			arrArgs[Channel.METHOD] = 'set_tag';
			return self._commonProcess(arrArgs)
		except ChannelException, e:
			self._channelExceptionHandler(e)
			return False


	#查询消息标签信息
	#用户关注：是
	def fetchTag(self, optional = None):
		"""
		查询消息标签信息
		参数:
			optional:可选参数
		返回值：
			成功：python字典； 失败：False
		"""
		try:
			tmpArgs = [optional]
			arrArgs = self._mergeArgs([], tmpArgs)
			arrArgs[Channel.METHOD] = 'fetch_tag';
			return self._commonProcess(arrArgs)
		except ChannelException, e:
			self._channelExceptionHandler(e)
			return False


	#删除消息标签
	#用户关注：是
	def deleteTag(self, tagName, optional = None):
		"""
		删除消息标签
		参数：
			tagName:标签
			optional:可选参数
		返回值：
			成功：python字典； 失败：False
		"""
		try:
			tmpArgs = [tagName, optional]
			arrArgs = self._mergeArgs([Channel.TAG_NAME], tmpArgs)
			arrArgs[Channel.METHOD] = 'delete_tag';
			return self._commonProcess(arrArgs)
		except ChannelException, e:
			self._channelExceptionHandler(e)
			return False



	#查询用户相关的标签
	#用户关注：是
	def queryUserTag(self, userId, optional = None):
		"""
		查询用户相关的标签
		参数：
			userId:用户id
			optional:可选参数
		返回值：
			成功：python字典； 失败：False
		"""
		try:
			tmpArgs = [userId, optional]
			arrArgs = self._mergeArgs([Channel.USER_ID], tmpArgs)
			arrArgs[Channel.METHOD] = 'query_user_tags';
			return self._commonProcess(arrArgs)
		except ChannelException, e:
			self._channelExceptionHandler(e)
			return False


	#根据channelId查询设备类型
	#用户关注：是
	def queryDeviceType(self, channelId, optional = None):
		"""
		根据channelId查询设备类型
		参数：
			ChannelId:用户Channel的ID号
			optional:可选参数
		返回值：
			成功：python字典； 失败：False
		"""
		try:
			tmpArgs = [channelId, optional]
			arrArgs = self._mergeArgs([Channel.CHANNEL_ID], tmpArgs)
			arrArgs[Channel.METHOD] = 'query_device_type';
			return self._commonProcess(arrArgs)
		except ChannelException, e:
			self._channelExceptionHandler(e)
			return False



	#
	# 内部函数
	#

	def _checkString(self, string, minLen, maxLen):
		if( isinstance(string, str) and len(string) >= minLen 
			and len(string) <= maxLen ):
			return True
		else:
			return False


	def _adjustOpt(self, opt):
		if(not ((opt is not None) and isinstance(opt, dict))):
			raise ChannelException('no params are set', Channel.CHANNEL_SDK_PARAM)
		if(not opt.has_key(Channel.TIMESTAMP)):
			opt[Channel.TIMESTAMP] = int(time.time())
		opt[Channel.HOST] = Channel.DEFAULT_HOST 
		opt[Channel.API_KEY] = self._apiKey
		if(opt.has_key(Channel.SECRET_KEY)):
			del opt[Channel.SECRET_KEY]


	def _genSign(self, method, url, arrContent):
		gather = method + url
		keys = arrContent.keys()
		keys.sort()
		for key in keys:
			gather += key + '=' + str(arrContent[key])
		gather += self._secretKey
		sign = hashlib.md5(urllib.quote_plus(gather))  
		return sign.hexdigest()


	def _baseControl(self, opt):
		resource = 'channel'
		if( opt.has_key(Channel.CHANNEL_ID) ):
			if(opt[Channel.CHANNEL_ID] is not None and opt[Channel.METHOD] not in self._method_channel_in_body):
				resource = opt[Channel.CHANNEL_ID]
				del opt[Channel.CHANNEL_ID]
		
		host = opt[Channel.HOST]
		del opt[Channel.HOST]
		url = 'http://' + host + '/rest/2.0/' + Channel.PRODUCT + '/'
		url += resource
		http_method = 'POST'
		opt[Channel.SIGN] = self._genSign(http_method, url, opt)
		request = RequestCore(url)
		headers = dict()
		headers['Content-Type'] = 'application/x-www-form-urlencoded'
		headers['User-Agent'] = 'Baidu Channel Service Pythonsdk Client'

		for (headerKey , headerValue) in headers.items():
			headerValue = headerValue.replace('\r', '')
			headerValue = headerValue.replace('\n', '')
			if (headerValue is not None):
				request.add_header(headerKey, headerValue)
		
		request.set_method(http_method)
		request.set_body(urllib.urlencode(opt))
		
		if(isinstance(self._curlOpts, dict)):
			request.set_curlopts(self._curlOpts)

		request.handle_request()
		return ResponseCore(request.get_response_header(),
							request.get_response_body(),
							request.get_response_code())


	def _commonProcess(self, paramOpt):
		self._adjustOpt(paramOpt)
		ret = self._baseControl(paramOpt)
		if( ret is None):
			raise ChannelException('base control returned None object', 
			Channel.CHANNEL_SDK_SYS)
		if(ret.isOK()):
			result = json.loads(ret.body)
			if (result is None):
				raise ChannelException(ret.body, 
					Channel.CHANNEL_SDK_HTTP_STATUS_OK_BUT_RESULT_ERROR)
			self._requestId = result['request_id']
			return result
		result = json.loads(ret.body)
		if(result is None):
			raise ChannelException('ret body:' + ret.body,
				Channel.CHANNEL_SDK_HTTP_STATUS_ERROR_AND_RESULT_ERROR)
		self._requestId = result['request_id']
		raise ChannelException(result['error_msg'], result['error_code'])


	def _mergeArgs(self, arrNeed, tmpArgs):
		arrArgs = dict()
		if( len(arrNeed) == 0 and len(tmpArgs) == 0):
			return arrArgs
		if(len(tmpArgs)-1 != len(arrNeed) and len(tmpArgs) != len(arrNeed)):
			keys = '('
			for key in arrNeed:
				keys += key + ','
			if(key[-1] == '' and key[-2] == ','):
				keys = keys[0:-2]
			keys += ')'
	
			raise ChannelException('invalid sdk, params, params' + keys + 'are need', Channel.CHANNEL_SDK_PARAM)
		if(len(tmpArgs)-1 == len(arrNeed) and tmpArgs[-1] is not None 
			and (not isinstance(tmpArgs[-1], dict)) ):
			raise ChannelException ('invalid sdk params, optional param must bean dict', Channel.CHANNEL_SDK_PARAM)

		idx = 0
		if(isinstance(arrNeed, list)):
			for key in arrNeed:
				if(tmpArgs[idx] is None):
					raise ChannelException ('lack param ' + key, Channel.CHANNEL_SDK_PARAM)
				arrArgs[key] = tmpArgs[idx]	
				idx = idx + 1

		if(len(tmpArgs)  == idx + 1 and tmpArgs[idx] is not None):
			for (key, value) in tmpArgs[idx].items():
				if(not arrArgs.has_key(key) and value is not  None):
					arrArgs[key] = value

		return arrArgs	


	def _channelExceptionHandler(self, ex):
		print ex.error_msg, self._arrayErrorMap[ex.error_code]		
		
	
			 


