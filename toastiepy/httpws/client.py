class HTTPFrame:
    def __init__(self, reader):
        self._stream = reader
    
    async def parse(self):
        httpMessage = (await self._stream.read(8192)).decode('utf8')
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
            for idx in range(0,len(headerValues)):
                self.headers[headerName].append(headerValues[idx].strip(" \t"))
        body = part[2]
        self.body = body

class client:
    def __init__(self, rx, tx):
        self._rx = rx
        self._tx = tx
        self._httpFrame = HTTPFrame(rx)
    
    async def parse(self):
        await self._httpFrame.parse()
        self.method = self._httpFrame.method
        self.path = self._httpFrame.path
        self.httpVersion = self._httpFrame.httpVersion
        self.headers = self._httpFrame.headers
        self.body = self._httpFrame.body