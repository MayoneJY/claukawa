from claukawa.event_mapping import classify, truncate


def test_session_start():
    c = classify({"hook_event_name": "SessionStart", "source": "startup"})
    assert c.category == "session_start"
    assert "startup" in c.bubble_text
    assert c.is_idle is False


def test_user_prompt_submit_uses_prompt():
    c = classify({"hook_event_name": "UserPromptSubmit", "prompt": "  hello  "})
    assert c.category == "thinking"
    assert c.bubble_text == "hello"


def test_pretooluse_edit():
    c = classify({
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "C:/foo/bar/baz.py"},
    })
    assert c.category == "editing"
    assert c.bubble_text == "baz.py"


def test_pretooluse_bash():
    c = classify({
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "npm test"},
    })
    assert c.category == "bashing"
    assert c.bubble_text == "npm test"


def test_pretooluse_bash_prefers_description():
    c = classify({
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {
            "command": "cd /tmp && python tools/generate_placeholder_gifs.py 2>&1",
            "description": "Regenerate MIT-safe placeholder GIFs",
        },
    })
    assert c.category == "bashing"
    assert c.bubble_text == "Regenerate MIT-safe placeholder GIFs"


def test_pretooluse_grep_pattern():
    c = classify({
        "hook_event_name": "PreToolUse",
        "tool_name": "Grep",
        "tool_input": {"pattern": "TODO"},
    })
    assert c.category == "reading"
    assert c.bubble_text == "TODO"


def test_pretooluse_task():
    c = classify({
        "hook_event_name": "PreToolUse",
        "tool_name": "Task",
        "tool_input": {"description": "investigate auth"},
    })
    assert c.category == "subagent"
    assert c.bubble_text == "investigate auth"


def test_pretooluse_agent_alias_for_task():
    c = classify({
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {"description": "explore codebase"},
    })
    assert c.category == "subagent"
    assert c.bubble_text == "explore codebase"


def test_pretooluse_mcp():
    c = classify({
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__notion__search",
        "tool_input": {},
    })
    assert c.category == "mcp"
    assert "notion" in c.bubble_text and "search" in c.bubble_text


def test_pretooluse_inside_subagent_keeps_state():
    # Child tool calls inside a subagent must not override the parent
    # Agent/Task's subagent category. Claude Code marks them with agent_id.
    c = classify({
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": "x.py"},
        "agent_id": "a0b77f56aaa001379",
        "agent_type": "Explore",
    })
    assert c.category is None
    assert c.bubble_text == ""


def test_pretooluse_unknown_tool_keeps_state():
    c = classify({
        "hook_event_name": "PreToolUse",
        "tool_name": "Unknown",
        "tool_input": {},
    })
    assert c.category is None
    assert c.bubble_text == "Unknown"


def test_notification():
    c = classify({"hook_event_name": "Notification", "message": "needs permission"})
    assert c.category == "waiting_input"
    assert c.bubble_text == "needs permission"


def test_stop_marks_idle():
    c = classify({"hook_event_name": "Stop"})
    assert c.category == "idle"
    assert c.is_idle is True


def test_session_end_marks_idle():
    c = classify({"hook_event_name": "SessionEnd", "reason": "logout"})
    assert c.category == "idle"
    assert c.is_idle is True
    assert "logout" in c.bubble_text


def test_post_tool_use_keeps_state():
    c = classify({"hook_event_name": "PostToolUse", "tool_name": "Edit"})
    assert c.category is None


def test_precompact():
    c = classify({"hook_event_name": "PreCompact", "trigger": "manual"})
    assert c.category == "compacting"


def test_truncate_short():
    assert truncate("abc", 10) == "abc"


def test_truncate_long():
    out = truncate("abcdefghij", 5)
    assert len(out) == 5
    assert out.endswith("…")


def test_truncate_strips_newlines():
    assert truncate("a\nb\rc", 10) == "a b c"
