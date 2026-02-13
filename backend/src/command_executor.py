"""
Command Execution Utilities

Provides safe, read-only command execution for agent requests.
"""

import os
import re
import subprocess
from typing import Optional, Dict

REQUEST_KEYWORDS = [
    "project",
    "repo",
    "repository",
    "codebase",
    "folder",
    "directory",
    "here",
    "in this",
    "in the",
    "path",
    "at"
]

MAX_OUTPUT_CHARS = 4000


def _truncate_output(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... (output truncated)"


def _run_command(args, cwd: Optional[str] = None) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=5,
        check=False
    )
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    output_parts = []
    if stdout:
        output_parts.append(stdout)
    if stderr:
        output_parts.append("[stderr]\n" + stderr)
    output = "\n".join(output_parts).strip() or "(no output)"
    return _truncate_output(output)


def _run_shell(command: str, cwd: Optional[str] = None) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        shell=True
    )
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    output_parts = []
    if stdout:
        output_parts.append(stdout)
    if stderr:
        output_parts.append("[stderr]\n" + stderr)
    output = "\n".join(output_parts).strip() or "(no output)"
    return _truncate_output(output)


def _extract_existing_path(message: str) -> Optional[str]:
    candidates = re.findall(r"/[^\s]+", message)
    for raw in candidates:
        cleaned = raw.rstrip(".,;:)\"]'")
        expanded = os.path.abspath(os.path.expanduser(cleaned))
        if os.path.exists(expanded):
            return expanded
    return None


def detect_command_request(message: str) -> Optional[Dict[str, str]]:
    stripped = message.strip()
    for prefix in ("/cmd", "/exec", "/run"):
        if stripped.startswith(prefix):
            command = stripped[len(prefix):].strip()
            if command:
                return {"type": "shell", "command": command}

    lower = stripped.lower()
    command_prefixes = (
        "git ", "gh ", "ls ", "pwd", "whoami", "cat ", "sed ", "head ", "tail ", "grep ",
        "find ", "tree", "npm ", "yarn ", "pnpm ", "python ", "pip ", "make ", "docker ", "kubectl "
    )
    if lower.startswith(command_prefixes):
        return {"type": "shell", "command": stripped}

    for verb in ("run ", "execute ", "please run ", "please execute "):
        if lower.startswith(verb):
            command = stripped[len(verb):].strip()
            if command:
                return {"type": "shell", "command": command}

    if not any(keyword in lower for keyword in REQUEST_KEYWORDS):
        return None

    path = _extract_existing_path(stripped)
    if not path:
        return None

    return {"type": "inspect_path", "path": path}


def execute_command_request(request: Dict[str, str]) -> str:
    request_type = request.get("type")
    if request_type == "shell":
        command = request.get("command", "").strip()
        if not command:
            return "No command provided."
        return f"$ {command}\n{_run_shell(command)}"

    if request_type != "inspect_path":
        return "Unsupported command request."

    path = request.get("path")
    if not path or not os.path.exists(path):
        return f"Path not found: {path}"

    outputs = []
    outputs.append(f"$ ls -la {path}\n{_run_command(['ls', '-la', path])}")

    if os.path.isdir(path) and os.path.isdir(os.path.join(path, ".git")):
        outputs.append(
            f"$ git -C {path} status --short\n"
            f"{_run_command(['git', '-C', path, 'status', '--short'])}"
        )
        outputs.append(
            f"$ git -C {path} log -1 --oneline\n"
            f"{_run_command(['git', '-C', path, 'log', '-1', '--oneline'])}"
        )

    return _truncate_output("\n\n".join(outputs))


def extract_shell_commands(text: str) -> list[str]:
    if not text:
        return []
    commands = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("$ "):
            cmd = stripped.lstrip("$").strip()
            if cmd:
                commands.append(cmd)

    fenced = re.findall(r"```(bash|sh|shell)?\n([\s\S]*?)```", text, re.IGNORECASE)
    for lang, block in fenced:
        if not lang:
            continue
        for line in block.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                if stripped.startswith("$"):
                    stripped = stripped.lstrip("$").strip()
                commands.append(stripped)

    return commands
