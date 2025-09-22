import asyncio

class server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self._s = None
        async def begin():
            async def handler(reader, writer):
                pass
            self._s = await asyncio.start_server(handler, host, port)
        try:
            asyncio.run(begin())
        except KeyboardInterrupt:
            if self._s is not None:
                self._s.server_close()
    
    def begin(self):
        pass