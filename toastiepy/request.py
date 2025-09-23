from toastiepy import server

class request:
    def __init__(self, parent, socket, res, ip):
        self._parent = parent
        self._sock = socket
        self.res = res
        self.method = socket.method
        self.path = socket.path
        self.httpVersion = socket.httpVersion
        self.headers = socket.headers
        self.body = socket.body
        self.routeStack = []
        self.ip = ip
        self.baseUrl = ""
        self.data = None