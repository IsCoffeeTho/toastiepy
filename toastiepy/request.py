import asyncio
from toastiepy import server
from urllib.parse import urlparse, parse_qs, urlunparse

class request:
	def __init__(self, parent, socket, res, ip):
		self._parent = parent
		self._rx = socket._rx
		self._tx = socket._tx
		self._websocket = socket._websocket
		self.ip = ip
		self.baseUrl = ""
		url = urlparse(socket.path)
		self.path = url.path
		self.method = socket.method
		self.params = {}
		self.query = parse_qs(url.query)
		self.res = res
		self.cookies = {}
		if socket.headers.get("Cookie", None) is not None:
			for cookieLine in socket.headers["Cookie"]:
				cookies = cookieLine.split(";")
				for cookie in cookies:
					cookieName, _, cookieValue = cookie.partition("=")
					self.cookies[cookieName] = cookieValue
		self.routeStack = []
		self.stale = False
		if socket.headers.get("Cache-Control", []) == ["no-cache"]:
			self.stale = True
		self.headers = socket.headers
		self.originalUrl = urlunparse(url)
		self.hostname = url.hostname
		self.httpVersion = socket.httpVersion
		self.data = None
		self.body = socket.body
		self._upgraded = False
	
	async def upgrade(self, handler):
		self._upgraded = True
		if self._websocket._upgradeConnection(self, self.res):
			ret = handler(self._websocket)
			if asyncio.coroutines.iscoroutine(ret):
				await ret
			asyncio.create_task(self._websocket._activate())
			return True
		return False