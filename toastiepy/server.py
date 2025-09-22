import re
import socket
import asyncio
from toastiepy import httpws
from toastiepy.constants import PATH_PATTERN_LIKE

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
            if re.search(PATH_PATTERN_LIKE, path) is None:
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
                return path == route.path or path.startwith(routePath)
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
    
    def _trickleRequest(self, req, res, next):
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
            if req.headers["Upgrade"] is not None:
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
                    trickled = route.fn._trickleRequest(req, res, nextFn)
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
                    route.fn(req, res, nextFn)
                except Exception:
                    pass
            if not continueAfterCatch:
                break
        if continueAfterCatch:
            next()
        return caughtOnce
        
    def listen(self, host="127.0.0.1", port=8080):
        def wrapper(fn):
            self.host = host
            self.port = port
            self._s = httpws.server(host, port)
            fn(self)
            self._s.begin()
        return wrapper