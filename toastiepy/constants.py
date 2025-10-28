
PATH_LIKE = r'^([a-zA-Z0-9]|[\\/+_.-]|\%[0-9a-fA-F][0-9a-fA-F])+$'

COOKIE_NAME_LIKE = r'[_!#$%\'^+\.&`|~a-zA-Z0-9\-]'

PATH_PATTERN_LIKE = r'^(([a-zA-Z0-9]|[\/:+_.-]|\%[0-9a-fA-F][0-9a-fA-F])+\*?|\*)$'

def type(type):
    type_keys = {
        "application/octet-stream": [
            "",
            "bin",
            "binary",
            ".bin"
        ],
        "text/html": [
            "html",
            ".html",
            ".htm",
            ".htmx"
        ],
        "text/css": [
            "css",
            ".css",
            "stylesheet",
            "style"
        ],
        "application/javascript": [
            "js",
            ".js",
            "jsx",
            ".jsx",
            "ts",
            ".ts",
            "tsx",
            ".tsx"
        ],
        "application/json":[
            "json",
            "object",
            ".json",
            "dict",
            "list"
        ],
        "text/xml": [
            "xml",
            ".xml"
        ],
        "text/plain": [
            "text",
            "plain",
            "txt",
            ".txt"
        ],
    }
    
    for mimeType in type_keys.keys():
        for matchable in type_keys[mimeType]:
            if type == matchable:
                return mimeType
    return "text/plain"