from posix import stat
from toastiepy import constants
from datetime import datetime
from stat import S_ISREG
import json
import os
import re

def InvalidHeaderAccess():
    raise Exception("Invalid Header Access, cannot modify headers after sending.")

class response:
    def __init__(self, parent, req):
        self._parent = parent
        self._sock = req
        self._sentHeaders = False
        self._status = 200
        self._body = None
        self._cookies = {}
        self._headers = {}
        self._contentType = None
    
    def app(self):
        return self._parent
    
    def headerSent(self):
        return self._sentHeaders
    
    def get(self, headerField):
        return self._headers.get(headerField, [])
    
    def append(self, headerField, values):
        if isinstance(values, str):
            values = [values]
        if self._headers.get(headerField, None) is None:
            self._headers[headerField] = []
        for value in values:
            self._headers[headerField].append(value)
        return self
    
    def cookie(self, name, value, options={}):
        if self._sentHeaders:
            InvalidHeaderAccess()
        if re.search(constants.COOKIE_NAME_LIKE, name) is None:
            raise SyntaxError(f'cookie name "{name}" has invalid characters')
        options["value"] = value
        self._cookies[name] = options
        return self
    
    def clearCookie(self, name):
        if self._sentHeaders:
            InvalidHeaderAccess()
        if re.search(constants.COOKIE_NAME_LIKE, name) is None:
            raise SyntaxError(f'cookie name "{name}" has invalid characters')
        self._cookies[name] = {
            "value": "",
            "maxAge": 0,
            "path": "/"
        }
        return self
    
    def markNoCache(self, name):
        if self._sentHeaders:
            InvalidHeaderAccess()
        self._headers["Cache-Control"] = ["no-store"]
    
    def status(self, code):
        if self._sentHeaders:
            InvalidHeaderAccess()
        self._status = code
        return self
    
    def end(self):
        if self._sentHeaders:
            InvalidHeaderAccess()
        self._sentHeaders = True
        return True
    
    def send(self, body):
        self.end()
        if isinstance(body, bytes):
            self._body = body.decode('utf8')
            if self._contentType is None:
                self._contentType = "application/octet-stream"
            return
        if isinstance(body, dict) or isinstance(body, list):
            self._body = json.JSONEncoder().encode(body)
            if self._contentType is None:
                self._contentType = "application/json"
        else:
            self._body = f'{body}'
            if self._contentType is None:
                self._contentType = "text/plain"
    
    def sendStatic(self, path):
        statInfo = os.stat(path)
        if self._sock.headers.get("If-Modified-Since", None) is not None:
            modifiedSince = self._sock.headers["If-Modified-Since"][0]
            modifiedSince = datetime.strptime(modifiedSince, '%a, %d %b %Y %H:%M:%S')
            if modifiedSince.timestamp() >= statInfo.st_ctime:
                self._status = 304
                self.send("")
                return
        else:
            self._headers["Last-Modified"] = [datetime.fromtimestamp(statInfo.st_ctime).strftime('%a, %d %b %Y %H:%M:%S GMT')]
        return self.sendFile(path)
    
    def sendFile(self, path):
        try:
            statInfo = os.stat(path)
            if not S_ISREG(statInfo.st_mode):
                raise TypeError("Cannot send anything but a file")
            if statInfo.st_size == 0:
                self._body = ""
                if 200 >= self._status and self._status < 300:
                    self._status = 204
                    self.send("")
            else:
                self._body = open(path, "r").read(-1)
            if self._contentType == None:
                self.type(path.rpartition(".")[2])
            self.end()
        except Exception as err:
            return err
    
    def type(self, type):
        map = {
            "": "application/octet-stream",
            "bin": "application/octet-stream",
            "binary": "application/octet-stream",
            ".bin": "application/octet-stream",
            "text": "text/plain",
            "plain": "text/plain",
            "txt": "text/plain",
            ".txt": "text/plain",
            "html": "text/html",
            ".html": "text/html",
            ".htm": "text/html",
            ".htmx": "text/html",
            "json": "application/json",
            "object": "application/json",
            ".json": "application/json",
            "xml": "text/xml",
            ".xml": "text/xml"
        }
        self._contentType = map.get(type, type)
    
    def redirect(self, path):
        if self._sentHeaders:
            InvalidHeaderAccess()
        self._headers["Location"] = [path]
        if self._status < 300 or self._status >= 400:
            self._status = 307
        self._body = ""
        self.end()
    
    def _build_response(self):
        if self._contentType is not None:
            self._headers["Content-Type"] = [self._contentType]
        
        for cookieName in self._cookies:
            cookie = self._cookies[cookieName]
            cookieString = f"{cookieName}={cookie["value"]}"
            if cookie.get("expires", None) is not None:
                cookieString += f"; Expires={datetime.fromtimestamp(cookie["expires"]).strftime('%a, %d %b %Y %H:%M:%S GMT')}"
            if cookie.get("maxAge", None) is not None:
                cookieString += f"; Max-Age={cookie["maxAge"]}"
            if cookie.get("domain", None) is not None:
                cookieString += f"; Domain={cookie["domain"]}"
            if cookie.get("path", None) is not None:
                cookieString += f"; Path={cookie["path"]}"
            if cookie.get("secure", False):
                cookieString += "; Secure"
            if cookie.get("httpOnly", False):
                cookieString += "; HttpOnly"
            if self._headers.get("Set-Cookie", None) is not None:
                self._headers["Set-Cookie"] = []
            self._headers["Set-Cookie"].append(cookieString)
            
        def defaultStatusMessage(code):
            map = {
                100: "Continue",
                101: "Switching Protocols",
                102: "Processing",
                103: "Early Hints",
                200: "OK",
                201: "Created",
                202: "Accepted",
                203: "Non-Authoritative Information",
                204: "No Content",
                205: "Reset Content",
                206: "Partial Content",
                207: "Multi-Status",
                208: "Already Reported",
                226: "IM Used",
                300: "Multiple Choices",
                301: "Moved Permanently",
                302: "Found",
                303: "See Other",
                304: "Not Modified",
                305: "Use Proxy",
                306: "Switch Proxy",
                307: "Temporary Redirect",
                308: "Permanent Redirect",
                400: "Bad Request",
                401: "Unauthorized",
                402: "Payment Required",
                403: "Forbidden",
                404: "Not Found",
                405: "Method Not Allowed",
                406: "Not Acceptable",
                407: "Proxy Authentication Required",
                408: "Request Timeout",
                409: "Conflict",
                410: "Gone",
                411: "Length Required",
                412: "Precondition Failed",
                413: "Payload Too Large",
                414: "URI Too Long",
                415: "Unsupported Media Type",
                416: "Range Not Satisfiable",
                417: "Expectation Failed",
                418: "I'm a teapot",
                421: "Misdirected Request",
                422: "Unprocessable Conten",
                423: "Locked",
                424: "Failed Dependency",
                425: "Too Early",
                426: "Upgrade Required",
                428: "Precondition Required",
                429: "Too Many Requests",
                431: "Request Header Fields Too Large",
                451: "Unavailable For Legal Reasons",
                500: "Internal Server Error",
                501: "Not Implemented",
                502: "Bad Gateway",
                503: "Service Unavailable",
                504: "Gateway Timeout",
                505: "HTTP Version Not Supported",
                506: "Variant Also Negotiates",
                507: "Insufficient Storage",
                508: "Loop Detected",
                510: "Not Extended",
                511: "Network Authentication Required"
            }
            return map.get(code, "Unknown Response Code")
        response = f"{self._sock.httpVersion} {self._status} {defaultStatusMessage(self._status)}\r\n"
    
        for headerName in self._headers:
            for headerLine in self._headers[headerName]:
                response += f"{headerName}: {headerLine}\r\n"
        response += "\r\n"
        
        if self._body is not None and self._body != "":
            response += self._body
        return response