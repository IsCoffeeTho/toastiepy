from test import expect, test
import requests

endpoint = "http://127.0.0.1:3000"

@test("Text")
async def text():
	expect(requests.get(f"{endpoint}/").text).toBe("TEST SERVER")
	expect(requests.get(f"{endpoint}/test-route").text).toBe("Success for Test Route")
	expect(requests.get(f"{endpoint}/another-test-route").text).toBe("Success for Test Route again")
	expect(requests.get(f"{endpoint}/test-file").text).toBe("This text is from a file")

@test("JSON")
async def json():
	jsonfetch = requests.get(f"{endpoint}/json-test")
	
	expect(jsonfetch.headers.get("Content-Type")).toBe("application/json")

	jsontest = jsonfetch.json()
	expect(jsontest.get("text", None))._not.toBeNone()
	expect(jsontest["test"]).toBe("json")

@test("404")
async def err404():
	expect(requests.get(f"{endpoint}/not-a-handled-path").status_code).toBe(404)

@test("Redirection")
async def redirection():
	req = requests.get(f"{endpoint}/redirect")
	expect(req.is_redirect).toBeTrue()
	expect(req.url).toBe(f"{endpoint}/redirected")

@test("Asynchronous")
async def asynchronous():
	expect(requests.get(f"{endpoint}/async").status_code).toBe(200)