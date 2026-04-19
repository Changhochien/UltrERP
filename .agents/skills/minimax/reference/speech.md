# Speech / TTS Reference

**CLI:** `minimax speech <subcommand>`

## synthesize

**CLI:** `minimax speech synthesize [options]`

| Flag | Default | Description |
|------|---------|-------------|
| `--text, -t` | required | Text to synthesize (max 10,000 chars) |
| `--voice-id, -v` | required | Voice ID — preset, cloned, or designed |
| `--model, -m` | `speech-2.8-hd` | Model |
| `--speed` | `1.0` | Speed (0.5–2.0) |
| `--pitch` | `0` | Pitch adjustment (-12 to +12) |
| `--vol` | `1.0` | Volume (0–10) |
| `--emotion, -e` | null | `happy`, `sad`, `angry`, `fearful`, `disgusted`, `surprised`, `calm`, `fluent`, `whipser` |
| `--language-boost` | null | `auto`, `Chinese`, `English`, `Japanese`, `Korean` |
| `--audio-format, -f` | `mp3` | `mp3`, `pcm`, `flac`, `wav` |
| `--sample-rate` | null | 8000, 16000, 22050, 24000, 32000, 44100 |
| `--bitrate` | null | 32000, 64000, 128000, 256000 |
| `--output, -o` | null | Save decoded audio to file |

**Presets:** `Deep_Voice_Man`, `Wise_Woman`, `English_Insightful_Speaker`, etc.
**List all:** `minimax speech list-voices`

## long-create / long-query

For texts >10,000 chars (async, up to 50,000 chars).

```bash
minimax speech long-create --text "$(cat long-text.txt)" --voice-id <id>
minimax speech long-query <task_id>
```

## Voice Cloning

```bash
# 1. Upload audio (10s–5min, mp3/m4a/wav)
minimax speech upload --audio https://example.com/voice.mp3

# 2. Clone
minimax speech clone --file-id <file_id> --voice-id my_voice

# 3. Use
minimax speech synthesize --text "Hello" --voice-id my_voice
```

## Voice Design

```bash
minimax speech design \
  --prompt "Warm professional female narrator" \
  --preview "Precision rubber belts since 1988." \
  --voice-id narrator_voice
```

## Examples

```bash
# Basic
minimax speech synthesize --text "Your belt. In stock." \
  --voice-id Deep_Voice_Man --emotion calm --output audio.mp3

# Non-English
minimax speech synthesize --text "精密ラバーベルト" \
  --voice-id Japanese_Speaker --language-boost Japanese
```
