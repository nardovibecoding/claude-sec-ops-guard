#!/usr/bin/env python3
# Copyright (c) 2026 Nardo (nardovibecoding). AGPL-3.0 — see LICENSE
"""PreToolUse hook: canary file trip-wire.

Block Read tool when targeting a file named SECURITY_CANARY or CANARY.md.
Users place these in sensitive directories (~/.ssh/, ~/.aws/) as trip-wires
to detect prompt injection attacks directing the AI to read sensitive paths.
"""
import json
import sys
from pathlib import Path


_CANARY_NAMES = {"SECURITY_CANARY", "CANARY.md"}


def check(tool_name, tool_input, input_data):
    """Fire only on Read tool."""
    if tool_name != "Read":
        return False
    path_str = tool_input.get("file_path", "") or tool_input.get("path", "")
    if not path_str:
        return False
    name = Path(path_str).name
    return name in _CANARY_NAMES


def check_and_deny(tool_name, tool_input, input_data):
    """Return deny decision if canary file detected."""
    if not check(tool_name, tool_input, input_data):
        return None
    path_str = tool_input.get("file_path", "") or tool_input.get("path", "")
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny"
        },
        "systemMessage": (
            f"\u26a0\ufe0f CANARY TRIGGERED: AI attempted to read a security canary file at {path_str}. "
            "This may indicate a prompt injection attack directing the AI to read sensitive directories."
        )
    }


if __name__ == "__main__":
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        print("{}")
        sys.exit()
    result = check_and_deny(
        input_data.get("tool_name", ""),
        input_data.get("tool_input", {}),
        input_data
    )
    print(json.dumps(result or {}))
