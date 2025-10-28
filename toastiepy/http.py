from . import websock


class HTTPFrame:
    def __init__(self, reader):
        self._stream = reader

    async def parse(self):
        httpMessage = (await self._stream.read(-1)).decode('utf8')
        part = httpMessage.partition(' ')
        self.method = part[0]
        part = part[2].partition(' ')
        self.path = part[0]
        part = part[2].partition('\r\n')
        self.httpVersion = part[0]
        self.headers = {}
        while True:
            part = part[2].partition('\r\n')
            header = part[0]
            if header == '':
                break
            splitIdx = header.find(':')
            if splitIdx == -1:
                print("potential malformed header")
                continue
            headerName = header[:splitIdx]
            if self.headers.get(headerName, None) is None:
                self.headers[headerName] = []
            headerValues = header[splitIdx+1:].split(",")
            for idx in range(0, len(headerValues)):
                self.headers[headerName].append(headerValues[idx].strip(" \t"))
        body = part[2]
        if self.headers.get("Content-Length", None) is not None:
            length = self.headers["Content-Length"][0] or 0
            while len(body) < length:
                chunk = await self._stream.read(len(body) - length)
                if len(chunk) == 0:
                    break
                body += chunk
            if len(body) > length:
                body = body[:length]
        elif self.headers.get("Transfer-Encoding", [""])[0] == "Chunked":
            while True:
                chunk = await self._stream.read(-1)
                if len(chunk) == 0:
                    break
                body += chunk
        self.body = body


class client:
    def __init__(self, rx, tx):
        self._rx = rx
        self._tx = tx
        self._httpFrame = HTTPFrame(rx)
        self._websocket = websock.websocketClient((rx, tx))

    async def parse(self):
        await self._httpFrame.parse()
        self.method = self._httpFrame.method
        self.path = self._httpFrame.path
        self.httpVersion = self._httpFrame.httpVersion
        self.headers = self._httpFrame.headers
        self.body = self._httpFrame.body
        self.upgrade = self._websocket._upgradeConnection
