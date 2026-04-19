---
name: minimax
description: Generate images, speech, video, or music via MiniMax Token Plan APIs. Activates the appropriate minimax CLI subcommand based on modality. Use when asked to "generate an image", "create a product photo", "synthesize speech", "generate a video", or "create music". For detailed options, see reference/<modality>.md for the relevant modality.
argument-hint: "[modality] [description]"
version: 1.2.0
---

# MiniMax AI Generation

Use the `minimax` CLI to call MiniMax Token Plan APIs. Each modality is a separate subcommand.

**Requires:** `minimax` CLI installed and `MINIMAX_API_KEY` set.

---

## Modality Routing

| Request keywords | Subcommand |
|-----------------|------------|
| "image", "photo", "product shot", "picture" | `minimax image generate` |
| "speech", "tts", "voice", "synthesize", "audio", "talk" | `minimax speech synthesize` |
| "video", "clip", "animate" | `minimax video generate` |
| "music", "song", "track" | `minimax music generate` |

---

## Quick Examples

```bash
# Image
minimax image generate --prompt "A rubber belt on white" --aspect-ratio 16:9

# Speech
minimax speech synthesize --text "Your belt. In stock." --voice-id Deep_Voice_Man --emotion calm

# Video
minimax video generate --prompt "Conveyor belt in motion"

# Music
minimax music generate --prompt "Upbeat corporate" --instrumental
```

---

## Full Reference

Each modality has a dedicated reference file. Load only what you need:

| Modality | Reference file |
|----------|---------------|
| Image | `reference/image.md` |
| Speech | `reference/speech.md` |
| Video | `reference/video.md` |
| Music | `reference/music.md` |
