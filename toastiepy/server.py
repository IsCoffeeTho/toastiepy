from . import httpws, constants, response, request, websock
import asyncio
import inspect
import os
import re

from typing_extensions import Concatenate, ParamSpec
from typing import Any, Callable

P = ParamSpec('P')

NextFunction = Callable[..., Any]
HttpHandler = Callable[Concatenate[request.request, response.response, ...], Any]
WebSocketHandler = Callable[[websock.websocket], Any]

class _routeDescriptor:
	def __init__(self, method:str, path: str, handler):
		self.method = method
		self.path = path
		self.handler = handler

	def to_str(self):
		return f"<{self.method} {self.path}> => {self.handler}"

class server:
	def __init__(self, opts={}):
		self._routes = []
		self._running = False
		self.host = None
		self.port = None
		self._s = None

	def use(self, path="/", handler=None):
		if re.search(constants.PATH_PATTERN_LIKE, path) is None:
			raise TypeError("path is not PATH_PATTERN_LIKE")
		if not isinstance(handler, server):
			raise TypeError("use(path, handler): handler is not of toastiepy.server")
		self._routes.append(_routeDescriptor(
			method="MIDDLEWARE",
			path=path,
			handler=handler
		))
		return self

	def all(self, path: str):
		return self._addRoute("*", path)

	def get(self, path: str):
		return self._addRoute("GET", path)

	def put(self, path: str):
		return self._addRoute("PUT", path)

	def post(self, path: str):
		return self._addRoute("POST", path)

	def patch(self, path: str):
		return self._addRoute("PATCH", path)

	def delete(self, path: str):
		return self._addRoute("DELETE", path)

	def _addRoute(self, method:str, path: str):
		def wrapper(fn: HttpHandler):
			if re.search(constants.PATH_PATTERN_LIKE, path) is None:
				raise TypeError("path is not PATH_PATTERN_LIKE")
			handler = fn

			func_sig = inspect.signature(fn)
			num_args = len(func_sig.parameters)
			if num_args == 2:
				fn = fn
				def droppedNextHandler(req: request, res: response, next):
					return fn(req, res)
				handler = droppedNextHandler

			self._routes.append(_routeDescriptor(
				method=method,
				path=path,
				handler=handler
			))
			return fn
		return wrapper

	def websocket(self, path: str):
		def wrapper(fn: WebSocketHandler):
			if re.search(constants.PATH_PATTERN_LIKE, path) is None:
				raise TypeError("path is not PATH_PATTERN_LIKE")

			handler = fn

			self._routes.append(_routeDescriptor(
				method="WEBSOCKET",
				path=path,
				handler=handler
			))
			return fn
		return wrapper

	def _getRoutes(self, method, path):
		routes: list[_routeDescriptor] = []
		def _filter(route):
			if route.method == "MIDDLEWARE":
				routePath = route.path
				if route.path[-1] == '/':
					routePath = f"{route.path}/"
				return path == route.path or path.startswith(routePath)
			if route.method == "WEBSOCKET":
				if method != "GET":
					return False
			elif route.method != "*" and route.method != method:
				return False
			if route.path[-1] == '*':
				return path.startswith(route.path[0:-1])
			if route.path.find(':') != -1:
				masterPath = route.path.split("/")
				candidatePath = path.split("/")
				if len(masterPath) != len(candidatePath):
					return False
				for idx in range(1, len(masterPath)):
					key = masterPath[idx]
					if key[0] == ':':
						continue
					if key != candidatePath[idx]:
						return False
			return route.path == path
		for route in self._routes:
			if _filter(route):
				routes.append(route)
		return routes

	async def _trickleRequest(self, req, res, next):
		caughtOnce = False
		continueAfterCatch = False

		def nextFn():
			nonlocal continueAfterCatch
			continueAfterCatch = True
		methodRoutes = self._getRoutes(req.method, req.path)
		if len(methodRoutes) == 0:
			return False
		for route in methodRoutes:
			if route.path.find(":") != -1:
				masterPath = route.path.split("/")
				candidatePath = req.path.split("/")
				for idx in range(0, len(masterPath)):
					key = masterPath[idx]
					if key[-1] != ':':
						continue
					req.params[key[1:]] = candidatePath[idx]
			else:
				req.params = {}
			req.routeStack.append(route)
			continueAfterCatch = False
			if route.method == "WEBSOCKET":
				if req.headers.get("Upgrade", None) != ["websocket"]:
					continue
				await req.upgrade(route.handler)
				return True
			elif route.method == "MIDDLEWARE":
				savedPath = req.path
				req.path = req.path[len(route.path):]
				if req.path == "":
					req.path = "/"
				elif req.path[0] != '/':
					req.path = f'/{req.path}'
				trickleCaught = await route.handler._trickleRequest(req, res, nextFn)
				if trickleCaught:
					caughtOnce = True
				else:
					continueAfterCatch = True
				req.path = savedPath
			else:
				caughtOnce = True
				ret = route.handler(req, res, nextFn)
				if asyncio.coroutines.iscoroutine(ret):
					await ret
			if not continueAfterCatch:
				break
		if continueAfterCatch:
			next()
		return caughtOnce

	async def _requestHandler(self, client):
		res = response.response(self, client)
		req = request.request(
			self, client, res, client._tx.transport.get_extra_info("socket").getpeername())

		def _nothing():
			pass
		try:
			await self._trickleRequest(req, res, _nothing)
			if not res._sentHeaders:
				res.clear().status(405).send(f"Cannot {req.method} {req.path}")
				client._tx.close()
			if not req._upgraded:
				client._tx.close()
		except Exception as err:
			if not res._sentHeaders:
				res.clear().status(500).send(
					f"500 Internal Server Error\nUncaught: {err}")
			client._tx.close()
			raise err
			
	def _insertDefaultFavicon(self):
		faviconMissing = True
		for route in self._getRoutes("GET", "/favicon.ico"):
			if route.path.index("*") == -1:
				faviconMissing = False
				break
		if faviconMissing:
			faviconPath = f"{os.path.join(os.path.dirname(__file__)).rpartition("/")[0]}/assets/toastiepy.ico"
			def defaultFavicon(req, res, next):
				err = res.sendStatic(faviconPath)
				if err is not None:
					print("Error sending default '/favicon.ico':",err)
					next()
			self._routes.insert(0, _routeDescriptor(
				method="GET",
				path="/favicon.ico",
				handler=defaultFavicon
			))

	def listen(self, host="127.0.0.1", port=8080):
		self._insertDefaultFavicon()
		self.host = host
		self.port = port
		self._s = httpws.server(host, port, self._requestHandler)
		return self._s.begin()