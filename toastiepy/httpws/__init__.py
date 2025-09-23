import asyncio
from toastiepy.response import response
from toastiepy.request import request
from toastiepy.httpws.client import HTTPFrame, client

class server:
    def __init__(self, host, port, req_handler):
        self.host = host
        self.port = port
        self._req_handler = req_handler
        self._s = None
        
    async def _handler(self, reader, writer):
        httpStream = client(reader, writer)
        await httpStream.parse()
        await self._req_handler(httpStream)
    
    def begin(self):
        async def start():
            _s = None
            try:
                _s = await asyncio.start_server(self._handler, self.host, self.port)
                await _s.wait_closed()
            except asyncio.exceptions.CancelledError:
                pass
            except KeyboardInterrupt:
                if _s is not None:
                    _s.close()
        asyncio.run(start())