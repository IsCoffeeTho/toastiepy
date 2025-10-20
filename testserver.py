from random import randrange
import toastiepy

mockhost = "127.0.0.1"
mockport = randrange(1000, 9999)

mockserver = toastiepy.server()
    
@mockserver.get("/")
def index(req, res):
    res.send("TEST SERVER")

@mockserver.listen()
def listen_callback(server):
    print("Server Hooked!")