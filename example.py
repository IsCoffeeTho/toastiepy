import asyncio
import toastiepy

app = toastiepy.server()

__dirname = __file__.rpartition('/')[0]

@app.get("/fail")
def fail(req, res, next):
	err = res.sendStatic(f"{__dirname}/mockserver/")
	if err is not None:
		next()

@app.get("/async")
async def asynchronous(req, res):
	await asyncio.sleep(1)
	res.send("waited 1 sec before responding")

@app.get("/")
def index(req, res, next):
	err = res.sendStatic(f'{__dirname}/mockserver/index.html')
	if err is not None:
		print("missing index, moving on")
		next()

@app.websocket("/echo-ws")
async def echo_ws(ws):
	await ws.send(b"Hello")
	@ws.ondata
	async def ws_data_echo(data):
		await ws.send(data)
	@ws.onclose # needs work
	def ws_close(code, reason):
		print("websocket closed")

@app.get("/cookie/:name")
def cookie_blank(req, res):
	res.cookie(req.params["name"], "cookie").send("Set a Cookie!")

@app.get("/cookie/:name/:value")
def cookie_value(req, res):
	res.cookie(req.params["name"], req.params["value"]).send("Set a Cookie!")

@app.get("/multi-cookie")
def multicookie(req, res):
	res.cookie("cookie1", "hi")
	res.cookie("cookie2", "hi")
	res.send('Set two Cookies "cookie1" and "cookie2"!')

@app.get("/clear-cookie/:name")
def clearcookie(req, res):
	res.clearCookie(req.params["name"]).send("Cleared a Cookie!")

@app.get("/cookies")
def show_cookies(req, res):
	res.send(req.cookies)
	
@app.get("/file")
def empty(req, res, next):
	err = res.sendFile(f"{__dirname}/mockserver/test.txt")
	if err is not None:
		next()

@app.get("/redirect")
def redirect(req, res):
	res.redirect(f"/redirected?={req.path}")

@app.get("/redirected")
def redirected(req, res):
	res.send("redirected from redirect")

@app.get("/empty")
def empty(req, res, next):
	err = res.sendFile(f"{__dirname}/mockserver/emptyFile.txt")
	if err is not None:
		next()

@app.get("/long/path")
def long_path(req, res):
	res.send("This is an example long path route")

subserver = toastiepy.server()
app.use("/subserver", subserver)
app.use("/sub", subserver)

@subserver.get("/")
def subserver_index(req, res):
	err = res.sendFile(f"{__dirname}/mockserver/subserver.html")
	if err is not None:
		res.status(404).send(f"404 File Not Found\nERR: {err}")

@subserver.get("/*")
def subserver_catchall(req, res):
	res.status(404).send("404 on subserver")

_404_count = 0
@app.get("*")
def catchall(req, res):
	global _404_count
	_404_count += 1
	res.status(404).send(f"404 File Not Found\ntimes error occured {_404_count}")

def main():
	HOST = "127.0.0.1"
	PORT = 3000
	print(f"Hosting server @ {HOST}:{PORT}")
	return app.listen(HOST, PORT)

if __name__ == "__main__":
	asyncio.run(main())