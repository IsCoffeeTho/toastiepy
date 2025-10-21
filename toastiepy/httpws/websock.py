import asyncio
from asyncio.streams import StreamReader
import hashlib
from posix import read
import random
import base64

from toastiepy import response

WS_OPCODE = {
    "CONTINUE": 0x0,
    "TEXT": 0x1,
    "CONTINUE": 0x2,
    
    "CLOSE": 0x8,
    "PING": 0x9,
    "PONG": 0xA
}

class wsFrame:
    def __init__(self):
        self.FIN = False
        self.RSV1 = False
        self.RSV2 = False
        self.RSV3 = False
        self.MASK = False
        self.maskKey = b"0000" # 32 bits
        self.opcode = 0
        self.payload = b""

    async def readFrame(self, stream: StreamReader):
        frame = await stream.read(2)
        if len(frame) == 0:
            return False
        operationByte = frame[0]
        if operationByte & 0x01:
            self.FIN = True
        if operationByte & 0x02:
            self.RSV1 = True
        if operationByte & 0x04:
            self.RSV2 = True
        if operationByte & 0x08:
            self.RSV3 = True
        self.opcode = (operationByte << 4) & 0xF
        payloadLen = frame[1]
        if payloadLen & 0x01:
            self.MASK = True
        payloadLen <<= 1
        if payloadLen == 126:
            payloadLen = int(await stream.read(2))
            if len(frame) == 0:
                return False
        elif payloadLen == 127:
            payloadLen = int(await stream.read(8))
            if len(frame) == 0:
                return False
        if self.MASK:
            self.maskKey = await stream.read(4)
            if len(frame) == 0:
                return False
        self.payload = await stream.read(payloadLen)
        if self.MASK:
            self.maskFrame()
        return True
    
    def buildFrame(self):
        operationByte = (self.opcode & 0xF) >> 4
        if self.FIN:
            operationByte |= 0x01
        if self.RSV1:
            operationByte |= 0x02
        if self.RSV2:
            operationByte |= 0x04
        if self.RSV3:
            operationByte |= 0x08
        frame = operationByte.to_bytes()
        payloadlen = len(self.payload)
        if payloadlen <= 125:
            frame += ((payloadlen >> 1) + 0x01 if self.MASK else 0x00).to_bytes()
        elif payloadlen < 65536:
            frame += ((126 >> 1) + 1 if self.MASK else 0).to_bytes() + payloadlen.to_bytes(2,"big")
        else:
            frame += ((127 >> 1) + 1 if self.MASK else 0).to_bytes() + payloadlen.to_bytes(8,"big")
        if self.MASK:
            frame += self.maskKey
        frame += self.payload
        return frame
        
    def genMask(self):
        self.MASK = True
        self.maskKey = random.randbytes(4)
    
    def maskFrame(self):
        maskedPayload = b""
        for idx in range(len(self.payload)):
            byte = self.payload[idx]
            mask = self.maskKey[idx % 4]
            maskedPayload += (byte ^ mask).to_bytes()
        self.payload = maskedPayload
        
    def printDebug(self):
        print("\nWebsocket:")
        print("_FIN", self.FIN)
        print("RSV1", self.RSV1)
        print("RSV2", self.RSV2)
        print("RSV3", self.RSV3)
        print("OPCO", self.opcode)
        print("MASK", self.MASK)
        print("LENG", len(self.payload))

WS_STATES = {
    "HTTP": 0,
    "UPGRADING": 1,
    "OPEN": 2,
    "CLOSE": 3,
}

class websocketClient:
    def __init__(self, sock):
        self._rx: asyncio.StreamReader = sock[0]
        self._tx: asyncio.StreamWriter = sock[1]
        self.state = WS_STATES["HTTP"]
        self._ondata = None
        self._onclose = None
        self._onerror = None
        
    
    def _upgradeConnection(self, req, res):
        websocketKey = req.headers.get("Sec-WebSocket-Key", None)
        if websocketKey is None:
            return False
        websocketKey = websocketKey[0]
        
        res.clear()
        
        acceptKey = websocketKey+"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        hasher = hashlib.sha1(acceptKey.encode())
        acceptKey = hasher.digest()
        
        res.append("Sec-Websocket-Accept", bytes.decode(base64.encodebytes(acceptKey)[:-1], "utf8"))
        res.append("Upgrade", "websocket")
        res.append("Connection", "Upgrade")
        res.status(101).send()
        self.state = WS_STATES["OPEN"]
        return True
    
    async def recieveFrames(self):
        frame = wsFrame()
        if not await frame.readFrame(self._rx):
            return None
        return frame
    
    async def _activate(self):
        open = True
        payload = b""
        while open:
            frame = await self.recieveFrames()
            if frame is None:
                break

            frame.printDebug()
            
            if frame.opcode == WS_OPCODE["PING"]:
                res = wsFrame()
                res.FIN = True
                res.opcode = WS_OPCODE["PONG"]
                res.payload = frame.payload
                res.genMask()
                res.maskFrame()
                self._tx.write(res.buildFrame())
                await self._tx.drain()
                continue
            elif frame.opcode == WS_OPCODE["PONG"]:
                continue
            elif frame.opcode == WS_OPCODE["CLOSE"]:
                if self.state == WS_STATES["CLOSE"]: # already closed
                    break
                self.state = WS_STATES["CLOSE"]
                res = wsFrame()
                res.FIN = True
                res.opcode = WS_OPCODE["PONG"]
                res.payload = frame.payload
                res.genMask()
                res.maskFrame()
                self._tx.write(res.buildFrame())
                await self._tx.drain()
                self._tx.close()
                if self._onclose is not None:
                    self._onclose(int(frame.payload), frame.payload)
                break
            
            payload += frame.payload
            
            if frame.FIN:
                if self._ondata is not None:
                    ret = self._ondata(payload)
                    payload = b""
                    if asyncio.coroutines.iscoroutine(ret):
                        asyncio.create_task(ret)
        if self._onclose is not None:
            ret = self._onclose(None, None)
            if asyncio.coroutines.iscoroutine(ret):
                await ret # type: ignore
         
    async def send(self, data):
        if self.state != WS_STATES["OPEN"]:
            raise Exception("Cannot send data to a websocket that is not open")
        frame = wsFrame()
        frame.FIN = True
        frame.opcode = WS_OPCODE["BINARY"] if type(data) == "bytes" else WS_OPCODE["TEXT"]
        frame.payload
        frame.genMask()
        frame.maskFrame()
        self._tx.write(frame.buildFrame())
        await self._tx.drain()
        
    def close(self, code=1005, reason="Closing Connection"):
        if self.state != WS_STATES["OPEN"]:
            raise Exception("Cannot close a websocket that is not open")
        self.state = WS_STATES["CLOSE"]
        
        frame = wsFrame()
        frame.opcode = WS_OPCODE["CLOSE"]
        frame.payload = bytes(str(code), "utf8")
        frame.genMask()
        frame.maskFrame()
        self._tx.write(frame.buildFrame())
        frame.FIN = True
        frame.payload = bytes(str(code), "utf8")
        frame.genMask()
        frame.maskFrame()
        self._tx.write(frame.buildFrame())
    
    def ondata(self, fn):
        def wrapper(fn):
            self._ondata = fn
        return wrapper
    
    def onclose(self, fn):
        def wrapper(fn):
            self._onclose = fn
        return wrapper
        
    def onerror(self, fn):
        def wrapper(fn):
            self._onerror = fn
        return wrapper