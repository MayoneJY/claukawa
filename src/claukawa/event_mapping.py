from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

CATEGORIES = (
    "session_start",
    "thinking",
    "editing",
    "reading",
    "bashing",
    "web",
    "subagent",
    "mcp",
    "waiting_input",
    "idle",
    "compacting",
)

_EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
_READ_TOOLS = {"Read", "Grep", "Glob", "LS"}
_BASH_TOOLS = {"Bash", "PowerShell"}
_WEB_TOOLS = {"WebFetch", "WebSearch"}


@dataclass(frozen=True)
class Classification:
    category: str | None  # None means "keep current state on the window"
    bubble_text: str
    is_idle: bool


def classify(payload: dict[str, Any]) -> Classification:
    event = payload.get("hook_event_name") or ""
    if event == "SessionStart":
        source = payload.get("source") or "startup"
        return Classification("session_start", f"세션 시작 ({source})", False)
    if event == "UserPromptSubmit":
        prompt = (payload.get("prompt") or "").strip()
        return Classification("thinking", prompt or "생각 중", False)
    if event == "PreToolUse":
        # Tool calls made *inside* a subagent carry an `agent_id` (and
        # `agent_type`) linking them to the parent. Don't let those overwrite
        # the parent's `subagent` category — keep the current GIF and bubble
        # so the user sees one stable cup_phone state for the whole subagent
        # lifetime.
        if payload.get("agent_id"):
            return Classification(None, "", False)
        return _classify_pre_tool(payload)
    if event == "PostToolUse":
        return Classification(None, "", False)
    if event == "Notification":
        msg = (payload.get("message") or "입력 대기").strip()
        return Classification("waiting_input", msg, False)
    if event == "Stop":
        return Classification("idle", "응답 완료", True)
    if event == "SessionEnd":
        reason = payload.get("reason") or "other"
        return Classification("idle", f"세션 종료 ({reason})", True)
    if event == "PreCompact":
        trigger = payload.get("trigger") or "auto"
        return Classification("compacting", f"컨텍스트 압축 ({trigger})", False)
    if event == "SubagentStop":
        return Classification(None, "", False)
    return Classification(None, "", False)


def _classify_pre_tool(payload: dict[str, Any]) -> Classification:
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}

    if tool_name in _EDIT_TOOLS:
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        return Classification("editing", os.path.basename(path) or tool_name, False)
    if tool_name in _READ_TOOLS:
        path = tool_input.get("file_path") or tool_input.get("path") or ""
        pattern = tool_input.get("pattern") or tool_input.get("query") or ""
        text = os.path.basename(path) if path else pattern
        return Classification("reading", text or tool_name, False)
    if tool_name in _BASH_TOOLS:
        cmd = (tool_input.get("command") or "").strip()
        return Classification("bashing", cmd or tool_name, False)
    if tool_name in _WEB_TOOLS:
        target = tool_input.get("url") or tool_input.get("query") or ""
        return Classification("web", target or tool_name, False)
    if tool_name in ("Task", "Agent"):
        desc = (
            tool_input.get("description")
            or tool_input.get("subagent_type")
            or "subagent"
        )
        return Classification("subagent", desc, False)
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        # mcp__server__tool -> "server / tool"
        label = " / ".join(parts[1:]) if len(parts) >= 2 else tool_name
        return Classification("mcp", label, False)
    # Unknown tool: keep current state, just show tool name in bubble
    return Classification(None, tool_name, False)


def truncate(text: str, max_chars: int) -> str:
    text = (text or "").strip().replace("\n", " ").replace("\r", " ")
    if len(text) <= max_chars:
        return text
    return text[: max(1, max_chars - 1)] + "…"
