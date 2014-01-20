#!/usr/bin/python
#
# Copyright (c) Andrea Micheloni 2011
#
# Part of the tutorial available at http://www.tankmiche.com/
#
#       This program is free software: you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation, either version 3 of the License, or
#       (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#       
#       You should have received a copy of the GNU General Public License
#       along with this program.  If not, see <http://www.gnu.org/licenses/>.

import threading

class EventQueue:
	def __init__(self):
		self._queue = self.Queue()
		self._results = self.Results()
		self._runner = self.Runner(self._queue.dequeue)

		self._runner.start()

	def enqueue(self, func, args=[], kwargs={}, highPriority = False, callback = None):
		(setResultFunc, getResultFunc) = self._results.getResultContainer()
		element = self.Runner.packCall(func, args, kwargs, setResultFunc, getResultFunc, callback)

		if self._runner.isRunning():
			self._queue.enqueue(element, highPriority)
		else:
			self._runner.flagError(
				element,
				message="Event has been added after the stop() event.")

		return getResultFunc

	def stop(self, highPriority = False):
		(setResultFunc, getResultFunc) = self._results.getResultContainer()
		element = self._runner.getStopCall(self._flushQueue, setResultFunc)
		self._queue.enqueue(element, highPriority)

		return getResultFunc

	def _flushQueue(self):
		while self._queue.hasMore():
			element = self._queue.dequeue()
			self._runner.flagError(element)

	class Queue:
		def __init__(self):
			self._list = []
			self._condition = threading.Condition()

		def enqueue(self, element, highPriority):
			with self._condition:
				if highPriority:
					self._list.insert(0, element)
				else:
					self._list.append(element)
				self._condition.notify()

		def hasMore(self):
			with self._condition:
				return len(self._list) > 0

		def dequeue(self):
			with self._condition:
				while not self.hasMore():
					self._condition.wait()
				return self._list.pop(0)

	class Results:
		def getResultContainer(self):
			container = self._Container()
			return (container.setResult, container.getResult)

		class _Container:
			def __init__(self):
				self._condition = threading.Condition()
				self._hasResult = False
				self._resultIsException = False
				self._result = None

			def setResult(self, result, resultIsException):
				with self._condition:
					self._hasResult = True
					self._resultIsException = resultIsException
					self._result = result
					self._condition.notify()

			def getResult(self):
				with self._condition:
					while not self._hasResult:
						self._condition.wait()
					if self._resultIsException:
						raise self._result
					else:
						return self._result

	class Runner(threading.Thread):
		def __init__(self, getNextFunc):
			threading.Thread.__init__(self)
			self._running = True
			self._getNextFunc = getNextFunc
			self._stopLock = threading.Lock()

		def run(self):
			while self.isRunning():
				next = self._getNextFunc()
				self._execute(next)

		def isRunning(self):
			with self._stopLock:
				return self._running

		def flagError(self, element, message="Event has not been processed."):
			(func, args, kwargs, setResultFunc, getResultFunc, callback) = element
			setResultFunc(UnprocessedEvent(message), resultIsException = True)

		def getStopCall(self, afterStopFunc, setResultFunc):
			return (self._stop, [afterStopFunc], {}, setResultFunc, None, None)

		@staticmethod
		def packCall(func, args, kwargs, setResultFunc, getResultFunc, callback = None):
			return (func, args, kwargs, setResultFunc, getResultFunc, callback)

		def _execute(self, element):
			(func, args, kwargs, setResultFunc, getResultFunc, callback) = element
			try:
				result = func(*args, **kwargs)
				setResultFunc(result, resultIsException = False)
			except Exception, exception:
				setResultFunc(exception, resultIsException = True)

                        if callback:
                             callback(getResultFunc)

		def _stop(self, afterStopFunc):
			with self._stopLock:
				self._running = False
				afterStopFunc()

class UnprocessedEvent(Exception):
	def __init__(self, reason):
		self._reason = reason

	def __str__(self):
		return str(self._reason)

	def __repr__(self):
		return "UnprocessedEvent(" + repr(self._reason) + ")"
