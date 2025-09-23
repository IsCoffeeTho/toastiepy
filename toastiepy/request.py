from toastiepy import server
from urllib.parse import urlparse, parse_qs, urlunparse

class request:
    def __init__(self, parent, socket, res, ip):
        self._parent = parent
        self._req = socket
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
            for cookieLine in self.headers["Cookie"]:
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