import re
from toastiepy.constants import PATH_PATTERN_LIKE

class server:
    def __init__(self, opts={}):
        self._routes = []
        self._running = False
        self.host = ""
        self.port = 0
    
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
            self._routes.append({
                "method": method,
                "path": path,
                "fn": fn
            })
        return wrapper
    
    def _getRoutes(self, method, path):
        routes = []
        for route in self._routes:
            if route.method == "MIDDLEWARE":
                if path == route.path or path.startwith(f"{route.path}/" if route.path[-1] == '/' else route.path):
                    routes.append(route)
                continue
            if route.method == "WS":
                if method != "GET":
                    continue
            if route.method != "*" and route.method != method:
                continue
            if route.path[-1] == '*':
                if path.startswith(route.path[0:-1]):
                    
                continue
        
        return routes
    
    def listen(self, host="127.0.0.1", port=8080):
        self.host = host
        self.port = port