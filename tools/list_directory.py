import os

LIST_DIRECTORY_SCHEMA = {
    "name": "list_directory",
    "description": "List files and subdirectories at a path. Use to navigate codebase structure and knowledge base before reading specific files.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the directory to list",
            }
        },
        "required": ["path"],
    },
}


def list_directory(path: str) -> str:
    if not os.path.exists(path):
        return f"Error: Path not found: {path}"
    if not os.path.isdir(path):
        return f"Error: Not a directory: {path}"
    try:
        entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name))
        if not entries:
            return f"{path}: (empty)"
        lines = [f"{path}:"]
        for e in entries:
            tag = "[dir] " if e.is_dir() else "[file]"
            lines.append(f"  {tag} {e.name}")
        return "\n".join(lines)
    except PermissionError:
        return f"Error: Permission denied: {path}"
