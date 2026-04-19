# Music Generation Reference

**CLI:** `minimax music <subcommand>`

## generate

| Flag | Default | Description |
|------|---------|-------------|
| `--prompt, -p` | required | Music style/mood (max 2000 chars) |
| `--lyrics, -l` | null | Song lyrics with `[Verse]`, `[Chorus]`, `[Bridge]` tags (1–3500 chars) |
| `--model, -m` | `music-2.5+` | Model |
| `--instrumental` | false | Instrumental only (no vocals) |
| `--auto-lyrics` | false | Auto-generate lyrics from prompt |
| `--audio-format, -f` | `mp3` | `mp3`, `wav`, `pcm` |
| `--sample-rate` | `44100` | Sample rate |
| `--bitrate` | `256000` | Bitrate |
| `--output, -o` | null | Save decoded audio to file |

## lyrics

Generate lyrics from a theme, then pass to `generate --lyrics`:

```bash
minimax music lyrics --prompt "Industrial anthem, Thailand factory, precision belts"
```

## Modes

**Instrumental:** `--instrumental` flag
**Full song:** `--lyrics` with structural tags
**Auto-lyrics:** `--auto-lyrics` (ignores `--lyrics`)

## Lyrics Format

Use section tags:
```
[Verse]    First verse...
[Chorus]   Main chorus...
[Verse 2]  Second verse...
[Chorus]   Repeat chorus...
[Bridge]   Bridge section...
[Outro]    Outro...
```

## Examples

```bash
# Instrumental
minimax music generate \
  --prompt "Upbeat corporate background music, positive energy" \
  --instrumental --output track.mp3

# Full song
minimax music generate \
  --prompt "Epic industrial anthem, heavy drums" \
  --lyrics "[Verse]
Factory floor, Thailand shore
Precision made, forevermore...
[Chorus]
Your belt, our craft..." \
  --output anthem.mp3

# Auto-generate lyrics
minimax music generate \
  --prompt "Dark cinematic underscore, tension building" \
  --auto-lyrics --output score.mp3

# Two-step workflow
minimax music lyrics --prompt "Thailand factory, precision belts, industrial strength"
# Copy generated lyrics, then:
minimax music generate --prompt "Energetic industrial" \
  --lyrics "<pasted lyrics>" --output song.mp3
```
