# Video Generation Reference

**CLI:** `minimax video <subcommand>`

## generate

| Flag | Default | Description |
|------|---------|-------------|
| `--prompt, -p` | required | Video description |
| `--model, -m` | `MiniMax-Hailuo-02` | Model |
| `--duration, -d` | `6` | Duration in seconds |
| `--resolution, -r` | `1080P` | Resolution |
| `--first-frame, -f` | null | First frame image URL or base64 (I2V) |
| `--last-frame, -l` | null | Last frame image URL or base64 (first-last-frame) |
| `--subject-ref` | null | Subject reference image URL or base64 (S2V-01) |
| `--subject-mode` | false | Enable S2V-01 subject_reference_mode |

**Models:** `MiniMax-Hailuo-02`, `MiniMax-Hailuo-2.3`, `S2V-01`

## Modes

**T2V:** `--prompt` only
**I2V:** `--prompt` + `--first-frame <image>`
**First-Last-Frame:** `--prompt` + `--first-frame` + `--last-frame`
**Subject-consistent (S2V-01):** Add `--subject-ref <image>` + `--subject-mode`

## query

Poll a video generation task:

```bash
minimax video query <task_id>
```

## retrieve

Retrieve a generated video file:

```bash
minimax video retrieve <file_id>
```

## Examples

```bash
# T2V
minimax video generate --prompt "A factory conveyor belt in motion, industrial setting"

# I2V
minimax video generate --prompt "Product slowly rotating" \
  --first-frame https://example.com/product.jpg

# First-last frame transition
minimax video generate --prompt "Day to night transition" \
  --first-frame https://example.com/day.jpg \
  --last-frame https://example.com/night.jpg

# Subject-consistent (S2V-01)
minimax video generate --prompt "Same person in factory" \
  --first-frame https://example.com/photo.jpg \
  --subject-ref https://example.com/portrait.jpg \
  --subject-mode

# Poll task
minimax video query <task_id>
```
