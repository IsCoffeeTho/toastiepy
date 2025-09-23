import asyncio
import toastiepy
import json

app = toastiepy.server()

@app.get("/fail")
def fail(req, res):
    err = res.sendStatic(f"{__path__}/mockserver/")
    if err:
        res.status(404).send(f"404 File Not Found\nERR: {err}")

@app.get("/async")
async def asynchronous(req, res):
    await asyncio.sleep(1)
    res.send("waited 1 sec before responding")

@app.get("/")
def index(req, res, next):
    err = res.sendStatic(f'{__path__}/mockserver/index.html')
    if err:
        print("missing index, moving on")
        next()

@app.websocket("/echo-ws")
def echo_ws(ws):    
    @ws.onData
    def ws_data_echo(data):
        ws.send(data)

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
    ret = {}
    for cookie in req.cookies:
        ret[cookie] = req.cookies[cookie].value
    res.send(ret)

@app.get("/redirect")
def redirect(req, res):
    res.redirect(f"/redirected?={req.path}")

@app.get("/redirected")
def redirected(req, res):
    res.send("redirected from redirect")

@app.get("/empty")
def empty(req, res):
    err = res.sendFile(f"{__path__}/mockserver/emptyFile.txt")
    if err:
        res.status(404).send("404\nThe file exists but is empty\n\nHand Written Error")

@app.get("/long/path")
def long_path(req, res):
    res.send("This is an example long path route")

subserver = toastiepy.server()
app.use("/sub", subserver)

@subserver.get("/")
def subserver_index(req, res):
    err = res.sendFile()
    if err:
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

@app.listen("127.0.0.1", 3000)
def main(app):
    print(f"Hosting server @ {app.host}:{app.port}")