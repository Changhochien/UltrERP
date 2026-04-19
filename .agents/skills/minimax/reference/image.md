# Image Generation Reference

**CLI:** `minimax image generate [options]`

## Parameters

| Flag | Default | Description |
|------|---------|-------------|
| `--prompt, -p` | required | Image description |
| `--aspect-ratio, -r` | null | `1:1`, `16:9`, `9:16`, `4:3`, `3:2`, `2:3`, `3:4`, `21:9`. Uses fixed standard resolutions. Mutually exclusive with `--width`/`--height`. |
| `--width, -w` | null | Custom width (512–2048, divisible by 8). Use instead of `--aspect-ratio` for custom sizes. Both `--width` and `--height` must be set. |
| `--height` | null | Custom height (512–2048, divisible by 8). Use with `--width` for custom resolutions. |
| `--model, -m` | `image-01` | Model identifier |
| `--response-format, -f` | `base64` | `base64` or `url` |
| `--number, -n` | `1` | Number of images (1–9) |
| `--image, -i` | null | Reference image URL or base64 for I2I |
| `--subject-ref` | null | Portrait URL for character-consistent I2I |
| `--seed, -s` | null | Integer seed for reproducible results |
| `--optimizer` | false | Enable prompt optimizer |
| `--output, -o` | null | Write first image to file |

## Supported Resolutions

### Via `--aspect-ratio` (fixed standard resolutions)

| Ratio | Output size |
|-------|------------|
| `1:1` | 1024×1024 |
| `16:9` | 1280×720 |
| `9:16` | 720×1280 |
| `4:3` | 1152×864 |
| `3:2` | 1248×832 |
| `2:3` | 832×1248 |
| `3:4` | 864×1152 |
| `21:9` | 1344×576 |

### Via `--width` + `--height` (custom, divisible by 8)

- Each dimension: **512–2048px**
- **2048×2048 square is rejected** (pixel limit); use `--width 1792 --height 1792` for max square
- Both `--width` and `--height` must be provided when using custom size

| Example | Result |
|---------|--------|
| `--width 2048 --height 1152` | 2048×1152 (≈16:9 widescreen) |
| `--width 2048 --height 864` | 2048×864 (≈21:9 ultra-wide) |
| `--width 2048 --height 528` | 2048×528 (≈21:9 cinematic) |
| `--width 1792 --height 1792` | 1792×1792 (max square) |
| `--width 1920 --height 1080` | 1920×1080 (1080p) |

## Modes

**T2I:** `--prompt` only
**I2I:** `--prompt` + `--image <url or base64>`
**Character-consistent I2I:** Add `--subject-ref <portrait-url>`

## Examples

```bash
# Product hero (T2I) — standard resolution
minimax image generate \
  --prompt "A precision rubber belt on white background, studio lighting" \
  --aspect-ratio 16:9 --output belt.jpg

# 2K widescreen (2048px wide)
minimax image generate \
  --prompt "A precision rubber belt on white background, studio lighting" \
  --width 2048 --height 1152 --output belt_2k.jpg

# Ultra-wide cinematic 21:9 at 2048px
minimax image generate \
  --prompt "Conveyor belt in factory, cinematic wide shot" \
  --width 2048 --height 528 --output factory_ultrawide.png

# Transform to industrial background (I2I)
minimax image generate \
  --prompt "Same product on dark industrial background" \
  --image https://example.com/product.jpg --aspect-ratio 16:9

# Character-consistent portrait
minimax image generate \
  --prompt "Same person wearing factory uniform" \
  --image https://example.com/photo.jpg \
  --subject-ref https://example.com/portrait.jpg
```
