import os

MAX_BYTES = 10 * 1024  # 10KB

FILE_READER_SCHEMA = {
    "name": "read_file",
    "description": "Read the contents of a local file. Maximum 10KB. Use for reading knowledge base markdown files and codebase source files.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute or relative path to the file",
            }
        },
        "required": ["path"],
    },
}


def read_file(path: str) -> str:
    if not os.path.exists(path):
        return f"Error: File not found: {path}"
    if not os.path.isfile(path):
        return f"Error: Not a file: {path}"
    size = os.path.getsize(path)
    if size > MAX_BYTES:
        return f"Error: File too large ({size} bytes, max {MAX_BYTES})."
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"
