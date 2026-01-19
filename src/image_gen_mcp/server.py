"""FastMCP server for image generation."""

import os
import re
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP

from .client import ImageGenClient, ImageGenError
from .models import (
    AspectRatio,
    GeneratedImage,
    GenerationResult,
    ImageListItem,
    ImageSize,
    Settings,
)

# Initialize the MCP server
mcp = FastMCP(
    "image-gen-mcp",
    instructions="Generate images using laozhang.ai Gemini 3 Pro API and save to Obsidian vault",
)

# Global client instance (initialized lazily)
_client: ImageGenClient | None = None
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_client() -> ImageGenClient:
    """Get or create the API client instance."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = ImageGenClient(settings.laozhang_api_key)
    return _client


def get_output_dir() -> Path:
    """Get the output directory for generated images."""
    settings = get_settings()
    vault_path = Path(settings.obsidian_vault_path).expanduser()
    output_dir = vault_path / settings.ai_graphics_folder
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def format_file_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def generate_filename_from_prompt(prompt: str, suffix: str = "") -> str:
    """Generate a descriptive filename from the prompt.

    Extracts the first few significant words from the prompt,
    sanitizes them, and prepends today's date.

    Args:
        prompt: The image generation prompt
        suffix: Optional suffix (e.g., "_v1", "_v2")

    Returns:
        Filename like "2026-01-19_cute_robot_waving.jpg"
    """
    # Words to skip when extracting key terms
    skip_words = {
        "a", "an", "the", "in", "on", "at", "to", "for", "of", "with",
        "and", "or", "but", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "must", "shall",
        "can", "very", "really", "just", "also", "that", "this",
        "style", "image", "picture", "photo", "photograph", "illustration",
    }

    # Clean and tokenize the prompt
    # Remove special characters but keep spaces
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", prompt.lower())
    words = cleaned.split()

    # Extract significant words (skip common words, keep first 5)
    key_words = []
    for word in words:
        if word not in skip_words and len(word) > 1:
            key_words.append(word)
            if len(key_words) >= 5:
                break

    # If we didn't get any words, use first few words regardless
    if not key_words:
        key_words = words[:3]

    # Build filename
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    name_part = "_".join(key_words) if key_words else "generated"

    return f"{date_prefix}_{name_part}{suffix}.jpg"


def save_image(image_bytes: bytes, filename: str) -> GeneratedImage:
    """Save image bytes to the output directory.

    Args:
        image_bytes: Raw image data
        filename: Desired filename

    Returns:
        GeneratedImage with path and size info
    """
    output_dir = get_output_dir()
    filepath = output_dir / filename

    # Handle filename collision by adding a number
    counter = 1
    original_stem = filepath.stem
    while filepath.exists():
        filepath = output_dir / f"{original_stem}_{counter}.jpg"
        counter += 1

    filepath.write_bytes(image_bytes)

    return GeneratedImage(
        path=str(filepath),
        filename=filepath.name,
        size_bytes=len(image_bytes),
        size_human=format_file_size(len(image_bytes)),
    )


@mcp.tool()
async def generate_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    size: str = "2K",
) -> str:
    """Generate a single image from a text prompt.

    Args:
        prompt: Text description of the desired image
        aspect_ratio: Image aspect ratio. Options: 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3, 21:9, 9:21, 5:4 (default: 1:1)
        size: Image resolution. Options: 1K (fast), 2K (default), 4K (highest quality)

    Returns:
        Information about the generated and saved image
    """
    # Validate aspect ratio
    valid_ratios = [r.value for r in AspectRatio]
    if aspect_ratio not in valid_ratios:
        return f"Error: Invalid aspect ratio '{aspect_ratio}'. Valid options: {', '.join(valid_ratios)}"

    # Validate size
    valid_sizes = [s.value for s in ImageSize]
    if size not in valid_sizes:
        return f"Error: Invalid size '{size}'. Valid options: {', '.join(valid_sizes)}"

    try:
        client = get_client()
        images = await client.generate(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            size=size,
            num_images=1,
        )

        if not images:
            return "Error: No image was generated"

        # Save the image
        filename = generate_filename_from_prompt(prompt)
        saved = save_image(images[0], filename)

        return (
            f"Image generated successfully!\n\n"
            f"**File:** {saved.filename}\n"
            f"**Path:** {saved.path}\n"
            f"**Size:** {saved.size_human}\n\n"
            f"The image has been saved to your Obsidian vault's AI graphics folder."
        )

    except ImageGenError as e:
        return f"Error generating image: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def generate_multiple(
    prompt: str,
    count: int = 4,
    aspect_ratio: str = "1:1",
    size: str = "2K",
) -> str:
    """Generate multiple images from the same prompt.

    Useful for exploring different interpretations of your idea.

    Args:
        prompt: Text description of the desired image
        count: Number of images to generate (2-4, default: 4)
        aspect_ratio: Image aspect ratio. Options: 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3, 21:9, 9:21, 5:4 (default: 1:1)
        size: Image resolution. Options: 1K (fast), 2K (default), 4K (highest quality)

    Returns:
        Information about all generated and saved images
    """
    # Validate count
    if count < 2:
        count = 2
    elif count > 4:
        count = 4

    # Validate aspect ratio
    valid_ratios = [r.value for r in AspectRatio]
    if aspect_ratio not in valid_ratios:
        return f"Error: Invalid aspect ratio '{aspect_ratio}'. Valid options: {', '.join(valid_ratios)}"

    # Validate size
    valid_sizes = [s.value for s in ImageSize]
    if size not in valid_sizes:
        return f"Error: Invalid size '{size}'. Valid options: {', '.join(valid_sizes)}"

    try:
        client = get_client()
        images = await client.generate(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            size=size,
            num_images=count,
        )

        if not images:
            return "Error: No images were generated"

        # Save all images with variation suffixes
        saved_images: list[GeneratedImage] = []
        base_filename = generate_filename_from_prompt(prompt)
        base_stem = base_filename.replace(".jpg", "")

        for i, image_bytes in enumerate(images, 1):
            filename = f"{base_stem}_v{i}.jpg"
            saved = save_image(image_bytes, filename)
            saved_images.append(saved)

        # Format response
        total_size = sum(img.size_bytes for img in saved_images)
        lines = [
            f"Generated {len(saved_images)} variations!\n",
        ]

        for img in saved_images:
            lines.append(f"- **{img.filename}** ({img.size_human})")

        lines.append(f"\n**Total size:** {format_file_size(total_size)}")
        lines.append(f"**Location:** {get_output_dir()}")

        return "\n".join(lines)

    except ImageGenError as e:
        return f"Error generating images: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def generate_variations(
    image_paths: list[str],
    prompt: str,
    count: int = 4,
    aspect_ratio: str = "1:1",
    size: str = "2K",
) -> str:
    """Generate variations based on one or more reference images.

    Uses the provided image(s) as style/content reference to generate new variations.
    The prompt guides how the reference images should be interpreted or modified.

    Args:
        image_paths: List of paths to reference images (1-14 images supported)
        prompt: Text description guiding the variation (e.g., "in watercolor style", "make it more vibrant")
        count: Number of variations to generate (1-4, default: 4)
        aspect_ratio: Image aspect ratio. Options: 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3, 21:9, 9:21, 5:4 (default: 1:1)
        size: Image resolution. Options: 1K (fast), 2K (default), 4K (highest quality)

    Returns:
        Information about all generated and saved images
    """
    # Validate count
    if count < 1:
        count = 1
    elif count > 4:
        count = 4

    # Validate image_paths
    if not image_paths:
        return "Error: At least one image path is required"
    if len(image_paths) > 14:
        return "Error: Maximum 14 reference images supported"

    # Validate aspect ratio
    valid_ratios = [r.value for r in AspectRatio]
    if aspect_ratio not in valid_ratios:
        return f"Error: Invalid aspect ratio '{aspect_ratio}'. Valid options: {', '.join(valid_ratios)}"

    # Validate size
    valid_sizes = [s.value for s in ImageSize]
    if size not in valid_sizes:
        return f"Error: Invalid size '{size}'. Valid options: {', '.join(valid_sizes)}"

    # Load reference images
    reference_images: list[bytes] = []
    for img_path in image_paths:
        path = Path(img_path).expanduser()
        if not path.exists():
            return f"Error: Image not found: {img_path}"
        if not path.is_file():
            return f"Error: Not a file: {img_path}"
        try:
            reference_images.append(path.read_bytes())
        except Exception as e:
            return f"Error reading {img_path}: {e}"

    try:
        client = get_client()
        images = await client.generate(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            size=size,
            num_images=count,
            reference_images=reference_images,
        )

        if not images:
            return "Error: No images were generated"

        # Save all images (with variation suffixes only if multiple)
        saved_images: list[GeneratedImage] = []
        base_filename = generate_filename_from_prompt(prompt)
        base_stem = base_filename.replace(".jpg", "")

        for i, image_bytes in enumerate(images, 1):
            if len(images) == 1:
                filename = f"{base_stem}.jpg"
            else:
                filename = f"{base_stem}_var{i}.jpg"
            saved = save_image(image_bytes, filename)
            saved_images.append(saved)

        # Format response
        total_size = sum(img.size_bytes for img in saved_images)
        lines = [
            f"Generated {len(saved_images)} variations from {len(reference_images)} reference image(s)!\n",
        ]

        for img in saved_images:
            lines.append(f"- **{img.filename}** ({img.size_human})")

        lines.append(f"\n**Total size:** {format_file_size(total_size)}")
        lines.append(f"**Location:** {get_output_dir()}")

        return "\n".join(lines)

    except ImageGenError as e:
        return f"Error generating variations: {e.message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def list_generated_images(limit: int = 20) -> str:
    """List recently generated images in the AI graphics folder.

    Args:
        limit: Maximum number of images to list (default: 20)

    Returns:
        Formatted list of images with filenames, dates, and sizes
    """
    try:
        output_dir = get_output_dir()

        # Get all jpg/jpeg/png files
        image_files: list[tuple[Path, float, int]] = []
        for pattern in ["*.jpg", "*.jpeg", "*.png"]:
            for filepath in output_dir.glob(pattern):
                stat = filepath.stat()
                image_files.append((filepath, stat.st_mtime, stat.st_size))

        if not image_files:
            return f"No images found in {output_dir}"

        # Sort by modification time (newest first)
        image_files.sort(key=lambda x: x[1], reverse=True)

        # Limit results
        image_files = image_files[:limit]

        # Format output
        lines = [f"**Recent images in AI graphics folder** (showing {len(image_files)}):\n"]

        for filepath, mtime, size in image_files:
            date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            size_str = format_file_size(size)
            lines.append(f"- **{filepath.name}** | {date_str} | {size_str}")

        lines.append(f"\n**Folder:** {output_dir}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error listing images: {str(e)}"


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
