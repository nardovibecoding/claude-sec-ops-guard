#!/usr/bin/env python3
# Copyright (c) 2026 Nardo (nardovibecoding). AGPL-3.0 — see LICENSE
"""PostToolUse hook: lightweight prompt injection scan on tool output.

Fires on Read, Bash, WebFetch. Scans output for injection patterns.
Returns WARNING (not block) if patterns found. Kept fast — pure regex, no I/O.
"""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# --- Injection patterns (lightweight set, compiled once) ---
_TEXT_PATTERNS = re.compile(
    r"ignore\s+(?:all\s+)?previous\s+instructions|"
    r"you\s+are\s+now\b|"
    r"system\s+prompt|"
    r"\bdisregard\b|"
    r"do\s+not\s+follow|"
    r"\[INST\]|"
    r"<\|im_start\|>|"
    r"###\s*Instruction:",
    re.IGNORECASE
)

# Unicode tag characters U+E0000-U+E007F
_UNICODE_TAG_RANGE = re.compile(r"[\U000E0000-\U000E007F]")


def check(tool_name, tool_input, input_data):
    """Only fire on Read, Bash, WebFetch outputs."""
    return tool_name in ("Read", "Bash", "WebFetch")


def action(tool_name, tool_input, input_data):
    """Scan tool_result for injection patterns. Return warning string or None."""
    # Extract output text from tool_result
    tool_result = input_data.get("tool_result", "")
    if isinstance(tool_result, dict):
        tool_result = tool_result.get("content", "") or tool_result.get("output", "") or str(tool_result)
    if isinstance(tool_result, list):
        # MCP-style content blocks
        parts = []
        for block in tool_result:
            if isinstance(block, dict):
                parts.append(block.get("text", "") or block.get("content", ""))
            else:
                parts.append(str(block))
        tool_result = "\n".join(parts)

    if not tool_result or not isinstance(tool_result, str):
        return None

    # Fast scan — check text patterns
    findings = []
    match = _TEXT_PATTERNS.search(tool_result)
    if match:
        findings.append(f"text pattern: '{match.group()[:40]}'")

    # Check for unicode tag characters
    if _UNICODE_TAG_RANGE.search(tool_result):
        findings.append("unicode tag characters (U+E0000-U+E007F)")

    if not findings:
        return None

    return f"\u26a0\ufe0f Prompt injection pattern detected in tool output: {'; '.join(findings)}"


if __name__ == "__main__":
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        print("{}")
        sys.exit()

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if not check(tool_name, tool_input, input_data):
        print("{}")
        sys.exit()

    message = action(tool_name, tool_input, input_data)
    if message:
        print(json.dumps({"systemMessage": message}))
    else:
        print("{}")
