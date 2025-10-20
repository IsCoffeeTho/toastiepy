from asyncio.streams import StreamReader
import hashlib
from posix import read
import random
import base64

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
        frame = await stream.read()
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
        elif payloadLen == 127:
            payloadLen = int(await stream.read(8))
        if self.MASK:
            self.maskKey = await stream.read(4)
        self.payload = await stream.read(payloadLen)
        if self.MASK:
            self.maskFrame()
    
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

def emptyHandler(data):
    pass

class websocketClient:
    def __init__(self, sock):
        self._rx = sock[0]
        self._tx = sock[1]
        self._ondata = emptyHandler
        self._onclose = emptyHandler
        self._onerror = emptyHandler
    
    def _upgradeConnection(self, req, res):
        websocketKey = req.headers.get("Sec-Websocket-Key", None)
        if websocketKey is None:
            return False
        websocketKey = bytes.decode(base64.b64decode(websocketKey), "utf8")
        websocketVer = req.headers.get("Sec-Websocket-Version", None)
        if websocketVer is None:
            return False
        res.clear()
        
        acceptKey = websocketKey+"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        hasher = hashlib.sha1(acceptKey.encode())
        acceptKey = hasher.digest()
        res.append("Sec-Websocket-Accept", bytes.decode(base64.encodebytes(acceptKey), "utf8"))
        res.append("Upgrade", "websocket")
        res.append("Connection", "Upgrade")
        res.status(101).send("")
    
    def activate(self):
        
        
    def close(self, reason="Closing Connection"):
        
    
    def ondata(self):
        def wrapper(fn):
            self._ondata = fn
        return wrapper
    
    def onclose(self):
        def wrapper(fn):
            self._onclose = fn
        return wrapper
        
    def onerror(self):
        def wrapper(fn):
            self._onerror = fn
        return wrapper