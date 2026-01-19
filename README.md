# Image Generation MCP Server

An MCP (Model Context Protocol) server that generates images using the laozhang.ai Gemini 3 Pro API and saves them directly to your Obsidian vault.

## Features

- **`generate_image`** — Generate a single image from a text prompt
- **`generate_multiple`** — Generate 2-4 images from the same prompt (different interpretations)
- **`generate_variations`** — Transform reference image(s) with a style/modification prompt
- **`list_generated_images`** — List recently generated images

Images are automatically saved with descriptive filenames based on the prompt (e.g., `2026-01-19_cute_robot_waving.jpg`).

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- [laozhang.ai](https://laozhang.ai) API key

## Installation

```bash
git clone https://github.com/JasonBates/image-gen-mcp.git
cd image-gen-mcp
uv sync
```

## Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your settings:
   ```bash
   LAOZHANG_API_KEY=your-api-key-here
   OBSIDIAN_VAULT_PATH=~/path/to/your/vault
   AI_GRAPHICS_FOLDER=Assets/AI graphics
   ```

## Usage

### Adding to Claude Code

Add to your Claude Code MCP configuration (`~/.claude.json`):

```json
{
  "mcpServers": {
    "image-gen": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/image-gen-mcp", "image-gen-mcp"],
      "env": {
        "LAOZHANG_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector uv run image-gen-mcp
```

## Tools

### generate_image

Generate a single image from a text prompt.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `prompt` | (required) | Text description of the desired image |
| `aspect_ratio` | `"1:1"` | 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3, 21:9, 9:21, 5:4 |
| `size` | `"4K"` | 1K (fast), 2K (balanced), 4K (highest quality, default) |

### generate_multiple

Generate multiple fresh interpretations of the same prompt.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `prompt` | (required) | Text description |
| `count` | `4` | Number of images (2-4) |
| `aspect_ratio` | `"1:1"` | See above |
| `size` | `"4K"` | See above |
| `diversity` | `0.0` | Prompt variation level (0.0-1.0). 0.0 = identical prompts, 0.3 = subtle changes, 0.6 = style/mood variations, 1.0 = creative reinterpretations |

**Example with diversity:**
```
# Low diversity - subtle variations (lighting, minor details)
generate_multiple("a robot waving", count=4, diversity=0.3)

# High diversity - creative reinterpretations
generate_multiple("a robot waving", count=4, diversity=0.9)
→ "a vintage 1950s tin robot waving on a kitchen counter"
→ "a massive robot waving goodbye to a departing spaceship"
→ "a tiny robot waving from inside a snow globe"
→ "a robot made of flowers waving in a garden"
```

### generate_variations

Transform reference image(s) using a style/modification prompt.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `image_paths` | (required) | List of paths to reference images (1-14) |
| `prompt` | (required) | How to transform (e.g., "in watercolor style") |
| `count` | `4` | Number of variations (1-4) |
| `aspect_ratio` | `"1:1"` | See above |
| `size` | `"4K"` | See above |

**Example:** Take an existing robot image and generate pixel art and cyberpunk versions.

### list_generated_images

List recently generated images in the output folder.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `limit` | `20` | Maximum images to list |

## API Capabilities

The laozhang.ai Gemini 3 Pro API supports:

| Feature | Options |
|---------|---------|
| Aspect Ratios | 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3, 21:9, 9:21, 5:4 |
| Sizes | 1K (~1024px), 2K (~2048px), 4K (~4096px) |
| Reference images | Up to 14 for style/content guidance |

**Note:** The API generates one image per request. For multiple images, this server makes sequential requests automatically.

## Filename Generation

Filenames are auto-generated from your prompt:

1. Key terms extracted (skipping common words)
2. Sanitized (lowercase, underscores)
3. Date prefix added

Examples:
- Single: `2026-01-19_cute_robot_waving.jpg`
- Multiple: `2026-01-19_cute_robot_waving_v1.jpg`, `_v2.jpg`
- Variations: `2026-01-19_watercolor_style_var1.jpg`, `_var2.jpg`

## License

MIT
