from __future__ import annotations

import ast
from shutil import which


def analyze_syntax(path: str, content: str, language_id: str) -> dict:
    if language_id == "python":
        try:
            ast.parse(content, filename=path)
        except SyntaxError as exc:
            return {
                "tool": "python-ast",
                "status": "FINDINGS",
                "findings": [{
                    "file": path,
                    "line": exc.lineno,
                    "message": exc.msg,
                }],
            }
        return {"tool": "python-ast", "status": "AVAILABLE", "findings": []}

    optional_tool = {
        "javascript": "eslint",
        "typescript": "eslint",
    }.get(language_id)
    if optional_tool and which(optional_tool) is not None:
        return {
            "tool": optional_tool,
            "status": "AVAILABLE_NOT_INVOKED",
            "findings": [],
            "note": "Tool is installed, but project configuration is not executed or loaded in Phase C.",
        }
    return {
        "tool": optional_tool or f"{language_id}-parser",
        "status": "UNAVAILABLE",
        "findings": [],
    }