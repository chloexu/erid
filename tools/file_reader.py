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
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            size = os.path.getsize(path)
            return f"Error: File too large ({size} bytes, max {MAX_BYTES})."
        return content
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except IsADirectoryError:
        return f"Error: Not a file: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except UnicodeDecodeError:
        return f"Error: File is not valid UTF-8: {path}"
    except OSError as e:
        return f"Error reading file: {e}"
