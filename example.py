import asyncio
import toastiepy
import urllib.parse

app = toastiepy.server()

__dirname = __file__.rpartition('/')[0]

@app.get("/")
def index(req: toastiepy.request, res: toastiepy.response, next):
	# This function returns the exception
	err = res.sendFile(f'{__dirname}/mockserver/index.html')
	if err is not None:
		print("Missing index, moving on")
		next()

@app.get("/static/*")
def index_style(req: toastiepy.request, res: toastiepy.response, next):
	err = res.sendStatic(f'{__dirname}/mockserver{req.path}')
	if err is not None:
		print("Missing staticfile, moving on")
		next()

@app.get("/fail")
def fail(req: toastiepy.request, res: toastiepy.response, next):
	err = res.sendStatic(f"{__dirname}/mockserver/")
	if err is not None:
		next()

@app.get("/async")
async def asynchronous(req: toastiepy.request, res: toastiepy.response):
	await asyncio.sleep(1)
	res.send("Waited 1 sec before responding")

@app.get("/cookie/:name")
def cookie_blank(req: toastiepy.request, res: toastiepy.response):
	res.cookie(req.params["name"], "cookie").send("Set a Cookie!")

@app.get("/cookie/:name/:value")
def cookie_value(req: toastiepy.request, res: toastiepy.response):
	res.cookie(req.params["name"], req.params["value"]).send("Set a Cookie!")

@app.get("/multi-cookie")
def multicookie(req: toastiepy.request, res: toastiepy.response):
	res.cookie("cookie1", "hi")
	res.cookie("cookie2", "hi")
	res.send('Set two Cookies "cookie1" and "cookie2"!')

@app.get("/clear-cookie/:name")
def clearcookie(req: toastiepy.request, res: toastiepy.response):
	res.clearCookie(req.params["name"]).send("Cleared a Cookie!")

@app.get("/cookies")
def show_cookies(req: toastiepy.request, res: toastiepy.response):
	res.send(req.cookies)

@app.get("/file")
def text_file(req: toastiepy.request, res: toastiepy.response, next):
	err = res.sendFile(f"{__dirname}/mockserver/test.txt")
	if err is not None:
		next()

@app.get("/empty")
def empty(req: toastiepy.request, res: toastiepy.response, next):
	err = res.sendFile(f"{__dirname}/mockserver/emptyFile.txt")
	if err is not None:
		next()

@app.get("/redirect")
def redirect(req: toastiepy.request, res: toastiepy.response):
	res.redirect(f"/redirected?={req.path}")

@app.get("/redirected")
def redirected(req: toastiepy.request, res: toastiepy.response):
	res.send("Redirected from redirect")

@app.get("/long/path")
def long_path(req: toastiepy.request, res: toastiepy.response):
	res.send("This is an example long path route")

@app.get("/websocket")
def echo_ws_client(req: toastiepy.request, res: toastiepy.response, next):
	err = res.sendFile(f"{__dirname}/mockserver/websocket.html")
	if err is not None:
		next()

@app.websocket("/echo-ws")
async def echo_ws(ws: toastiepy.websocket):
	@ws.ondata
	async def ws_data_echo(data):
		await ws.send(data)
	@ws.onclose
	def ws_close(code, reason):
		# Could do some session management
		pass
	await ws.send(b"Connected")
	
@app.get("/say/:word")
def say_endpoint(req, res):
	res.send(req.params["word"])

@app.get("/form")
def form_endpoint(req: toastiepy.request, res: toastiepy.response, next):
	err = res.sendStatic(f'{__dirname}/mockserver/form.html')
	if err is not None:
		print("missing index, moving on")
		next()

@app.post("/form")
def form_handler(req: toastiepy.request, res: toastiepy.response):
	body = urllib.parse.parse_qs(req.body.decode("utf8"))
	res.send(body)

subserver = toastiepy.server()
if subserver:
	@subserver.get("/")
	def subserver_index(req: toastiepy.request, res: toastiepy.response, next):
		err = res.sendFile(f"{__dirname}/mockserver/subserver.html")
		if err is not None:
			next()
	
	@subserver.get("/*")
	def subserver_catchall(req: toastiepy.request, res: toastiepy.response):
		res.status(404).send("404 on subserver")
app.use("/subserver", subserver)
app.use("/sub", subserver)

_404_count = 0
@app.get("*")
def catchall(req: toastiepy.request, res: toastiepy.response):
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