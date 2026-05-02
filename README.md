# Claukawa

**English** · [한국어](README.ko.md)

Always-on-top desktop indicator that visualizes the working state of your Claude Code sessions. Receives Claude Code hook events through a local HTTP gateway and displays one GIF window per session (up to 5).

## Quick start

### Windows

1. Download `Claukawa-{version}-win.exe` from the latest GitHub Release.
2. Double-click to launch. On first run, accept the dialog that registers Claude Code hooks in `~/.claude/settings.json` (existing hooks are preserved; the original file is backed up).
3. Open any Claude Code session in a terminal — a GIF window appears for that session and updates as Claude works.

### macOS

1. Download `Claukawa-{version}-mac.dmg` (or `.app.zip`) from the latest GitHub Release.
2. Drag `Claukawa.app` to `/Applications`.
3. First launch: right-click → **Open** (Gatekeeper bypass; the app is unsigned in v1).
4. Same as Windows — accept the hook registration dialog and start a Claude Code session.

## Status categories

Each Claude Code hook event is mapped to one of 11 GIF categories:

| Category | Trigger |
| --- | --- |
| `session_start` | New Claude Code session started |
| `thinking` | User prompt submitted, Claude reasoning |
| `editing` | `Edit` / `Write` / `MultiEdit` / `NotebookEdit` |
| `reading` | `Read` / `Grep` / `Glob` |
| `bashing` | `Bash` / `PowerShell` |
| `web` | `WebFetch` / `WebSearch` |
| `subagent` | `Task` |
| `mcp` | Any `mcp__*` tool |
| `waiting_input` | Permission / notification request |
| `idle` | Response complete or session ended |
| `compacting` | Context compaction in progress |

The default character pack is a chroma-keyed PNG set bundled with the app.

## Customizing characters

Don't like the default look or want to ship your own character? Replace any category from inside the app.

1. Click the tray icon (Windows, in the `∧` overflow area) or menu-bar icon (macOS) → **Open settings**.
2. Open the **GIF** tab. All 11 categories are listed with a live preview.
3. Click **Change…** next to the category you want to swap → pick an image file.
4. The replacement applies immediately — the next matching hook event will display your image.

Supported formats: PNG (transparency recommended), GIF (animated supported), JPG, WEBP, BMP. If the source has a solid-color background, pre-processing it with a chroma-key step (alpha = transparent) gives the cleanest look.

To revert, click **Default** on the same row.

## Settings

Open from the system tray icon (Windows) or menu bar (macOS):

- **Slot policy** — what happens when a 6th session arrives while 5 windows are visible: `idle_only` (replace only idle windows; default), `lru` (replace the oldest), `reject` (ignore the new session).
- **Speech bubble trigger** — `hover_only` (default), `event_burst` (3-second flash on event), `always`, `off`.
- **Auto-start** — launch on login (Windows registry / macOS LaunchAgent).
- **Hook tab** — view registration status, register or unregister hooks.

## Architecture

```
[Claude Session A] ──┐
[Claude Session B] ──┼─→ POST 127.0.0.1:17135/event ─→ Dispatcher ─→ Per-session GIF window
[Claude Session C] ──┘
```

Single-process Python app. PySide6 GUI on the main thread, stdlib `http.server` on a worker thread, Qt signal/slot bridges across threads. No dependencies beyond `PySide6`, `Pillow`, `platformdirs`.

## Build from source

```bash
pip install -e ".[build,dev]"
python tools/generate_placeholder_gifs.py    # regenerate placeholder pack
pytest                                        # run tests
pyinstaller build/claukawa-win.spec           # Windows
pyinstaller build/claukawa-mac.spec           # macOS
```

## License

MIT.

