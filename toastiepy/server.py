from asyncio import coroutines
import re
from toastiepy import httpws
import toastiepy
from toastiepy.request import request
from toastiepy.response import response
from toastiepy import constants

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
        if server is None:
            raise TypeError("use(path, server): server is not of toastiepy.server")
        self._addCatch("MIDDLEWARE", path)(server)
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
        return self._addCatch("WS", path)
    def _addCatch(self, method, path):
        def wrapper(fn):
            if re.search(constants.PATH_PATTERN_LIKE, path) is None:
                raise TypeError("path is not PATH_PATTERN_LIKE")
            self._routes.append(_routeDescriptor(
                method=method,
                path=path,
                fn=fn
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
            if route.method == "WS":
                if method != "GET":
                    return False
            if route.method != "*" and route.method != method:
                return False
            if route.path[-1] == '*':
                return path.startswith(route.path[0:-1])
            if route.path.find(':') != -1:
                masterPath = route.path.split("/")
                candidatePath = path.split("/")
                if len(masterPath) != len(candidatePath):
                    return False
                for idx in range(0,len(masterPath)):
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
            if req.headers.get("Upgrade", None) is not None:
                if route.method != "WS":
                    continue
                caughtOnce = True
                # @TODO Implement
                req.upgrade()
            elif route.method == "MIDDLEWARE":
                savedPath = req.path
                req.path = req.path[len(route.path):]
                if req.path[0] != '/':
                    req.path = f'/{req.path}'
                trickled = False
                try:
                    trickled = await route.fn._trickleRequest(req, res, nextFn)
                except Exception:
                    trickled = True
                if trickled:
                    caughtOnce = True
                else:
                    continueAfterCatch = True
                req.path = savedPath
            else:
                caughtOnce = True
                try:
                    print(route.fn)
                    route.fn(req, res, nextFn)
                except Exception:
                    pass
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
            if res._sentHeaders:
                client._tx.write(bytes(res._build_response(), "utf8"))
            else:
                client._tx.write(bytes(f"HTTP/1.1 405 Method Not Allowed\r\nContent-Type: text/plain\r\nX-Powered-By: ToastiePy v{toastiepy.version}\r\n\r\nCannot {req.method} {req.path}", "utf8"))
        except Exception as err:
            client._tx.write(bytes(f"HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\nX-Powered-By: ToastiePy v{toastiepy.version}\r\n\r\n500 Internal Server Error\nUncaught: {err}", "utf8"))
        client._tx.close()

    def listen(self, host="127.0.0.1", port=8080):
        def wrapper(fn):
            self.host = host
            self.port = port
            self._s = httpws.server(host, port, self._requestHandler)
            fn(self)
            self._s.begin()
        return wrapper