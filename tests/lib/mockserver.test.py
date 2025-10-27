import asyncio
from os import fork
from test import test, expect
import toastiepy

mockserver = toastiepy.server()

@mockserver.get("/")
def index(req, res):
	res.send("TEST SERVER")

@test("begin server")
async def begin():
	mockhost = "127.0.0.1"
	mockport = 3000
	asyncio.create_task(mockserver.listen(mockhost, mockport))
	while mockserver._s._s is None:
		await asyncio.sleep(0.05)
	expect(mockserver.host).toBe(mockhost)
	expect(mockserver.port).toBe(mockport)