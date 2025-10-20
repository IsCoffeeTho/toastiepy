import asyncio
from toastiepy import httpws, constants
from toastiepy.response import response
from toastiepy.request import request
from asyncio import coroutines
import toastiepy
import inspect
import re

class _routeDescriptor:
    def __init__(self, method, path, fn):
        self.method = method
        self.path = path
        self.fn = fn

class server:
    def __init__(self, opts={}):
        self._routes = []
        self._running = False
        self.host = None
        self.port = None
        self._s = None
    
    def use(self, path="/", server=None):
        if re.search(constants.PATH_PATTERN_LIKE, path) is None:
            raise TypeError("path is not PATH_PATTERN_LIKE")
        if server is None:
            raise TypeError("use(path, server): server is not of toastiepy.server")
        self._routes.append(_routeDescriptor(
            method="MIDDLEWARE",
            path=path,
            fn=server
        ))
        return self
    
    def all(self, path):
        return self._addCatch("*", path)
    def get(self, path):
        return self._addCatch("GET", path)
    def put(self, path):
        return self._addCatch("PUT", path)
    def post(self, path):
        return self._addCatch("POST", path)
    def patch(self, path):
        return self._addCatch("PATCH", path)
    def delete(self, path):
        return self._addCatch("DELETE", path)
    def websocket(self, path):
        return self._addCatch("WEBSOCKET", path)
    def _addCatch(self, method, path):
        def wrapper(fn):
            if re.search(constants.PATH_PATTERN_LIKE, path) is None:
                raise TypeError("path is not PATH_PATTERN_LIKE")
            
            handler = fn
            
            if method != "WEBSOCKET":
                sig = inspect.signature(fn)
                num_args = len(sig.parameters)
                if num_args == 2:
                    async def wrapped(req, res, next):
                        return fn(req, res)
                    handler = wrapped
            
            self._routes.append(_routeDescriptor(
                method=method,
                path=path,
                fn=handler
            ))
        return wrapper
    
    def _getRoutes(self, method, path):
        routes = []
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
                for idx in range(1,len(masterPath)):
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
                for idx in range(0,len(masterPath)):
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
                req.upgrade(route.fn)
                return True
            elif route.method == "MIDDLEWARE":
                savedPath = req.path
                req.path = req.path[len(route.path):]
                if req.path == "":
                    req.path = "/"
                elif req.path[0] != '/':
                    req.path = f'/{req.path}'
                trickleCaught = await route.fn._trickleRequest(req, res, nextFn)
                if trickleCaught:
                    caughtOnce = True
                else:
                    continueAfterCatch = True
                req.path = savedPath
            else:
                caughtOnce = True
                ret = route.fn(req, res, nextFn)
                if coroutines.iscoroutine(ret):
                    await ret
            if not continueAfterCatch:
                break
        if continueAfterCatch:
            next()
        return caughtOnce

    async def _requestHandler(self, client):
        res = response(self, client)
        req = request(self, client, res, client._tx.transport.get_extra_info("socket").getpeername())
        def _nothing():
            pass
        try:
            await self._trickleRequest(req, res, _nothing)
            if not res._sentHeaders:
                res.clear().status(405).send(f"Cannot {req.method} {req.path}")
                client._tx.write(res._build_response())
                client._tx.close()
        except Exception as err:
            if not res._sentHeaders:
                res.clear().status(500).send(f"500 Internal Server Error\nUncaught: {err}")
                client._tx.write(res._build_response())
            client._tx.close()
            raise err

    def listen(self, host="127.0.0.1", port=8080):
        def wrapper(fn):
            self.host = host
            self.port = port
            self._s = httpws.server(host, port, self._requestHandler)
            fn(self)
            asyncio.create_task(self._s.begin())
        return wrapper