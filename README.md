# ToastiePy

[**`git`**](https://github.com/IsCoffeeTho/toastiepy) | [**`pypi`**](https://pypi.org/project/toastiepy/)

ToastiePy is an express like python based http server framework.

<img src="https://raw.githubusercontent.com/IsCoffeeTho/toastiepy/master/assets/toastiepy.svg" height="300px" alt="Toastie (The Cat)">

## Installation
```bash
pip install toastiepy
```
### Usage
```py
# main.py
import toastiepy

app = toastiepy.server()

@app.get("/")
def index(req, res): # function name does not matter 
	res.send("Hello from Toastiebun")

if __name__ == "__main__":
	asyncio.run(app.listen("127.0.0.1", 8000))
```
![Hello from TostiePy](./assets/HelloWorld.png)

## Development
```bash
# Unit Tests
python3 -m unittest # Not Implemented Yet

python3 example.py
```