---
name: minimax-support
description: MiniMax Token Plan CLI for web search and image understanding. Use when asked to "search the web", "look up", "find information online", "analyze an image", "describe this image", or "understand what's in this picture".
emoji: 🔍
metadata:
  openclaw:
    requires:
      bins:
        - minimax-support
    install:
      - id: uv-tool
        kind: sh
        command: uv tool install --from "git+https://github.com/Changhochien/minimax-support" minimax-support
---

# minimax-support

Token-efficient web search and image understanding via MiniMax Token Plan APIs.

**Requires:** `minimax-support` CLI and `MINIMAX_API_KEY` in `~/.config/minimax/creds.toml`

---

## Commands

### Web Search

```bash
minimax-support search "<query>"
minimax-support search "<query>" --related
```

### Image Understanding

```bash
minimax-support understand "<image>" --prompt "<question>"
minimax-support understand "https://example.com/photo.jpg" --prompt "What does this show?"
minimax-support understand ./local/image.png --prompt "Describe this image"
```

---

## When to Use

- User asks to "search for X", "look up", "find information online"
- User shares an image and asks what it contains
- User wants real-time web information
- User asks "what's in this screenshot/photo"
