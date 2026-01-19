"""Pydantic models for image generation API."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AspectRatio(str, Enum):
    """Supported aspect ratios for image generation."""
    SQUARE = "1:1"
    WIDE_16_9 = "16:9"
    TALL_9_16 = "9:16"
    STANDARD_4_3 = "4:3"
    TALL_3_4 = "3:4"
    PHOTO_3_2 = "3:2"
    TALL_2_3 = "2:3"
    ULTRAWIDE = "21:9"
    ULTRATALL = "9:21"
    CLASSIC_5_4 = "5:4"


class ImageSize(str, Enum):
    """Supported image sizes/resolutions."""
    SMALL = "1K"  # Fastest
    MEDIUM = "2K"  # Default balance
    LARGE = "4K"  # Highest quality


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    laozhang_api_key: str = Field(
        description="API key for laozhang.ai"
    )
    obsidian_vault_path: str = Field(
        default="~/Obsidian/VAULTS/Trinity",
        description="Path to Obsidian vault"
    )
    ai_graphics_folder: str = Field(
        default="110 Assets/AI graphics",
        description="Subfolder for AI-generated images within vault"
    )


class GeneratedImage(BaseModel):
    """Represents a successfully generated and saved image."""

    path: str = Field(description="Full path to the saved image file")
    filename: str = Field(description="Just the filename")
    size_bytes: int = Field(description="File size in bytes")
    size_human: str = Field(description="Human-readable file size")


class GenerationResult(BaseModel):
    """Result of an image generation operation."""

    success: bool
    images: list[GeneratedImage] = Field(default_factory=list)
    error: str | None = None
    prompt_used: str | None = None


class ImageListItem(BaseModel):
    """An image in the list of generated images."""

    filename: str
    path: str
    size_bytes: int
    size_human: str
    created: str  # ISO format date string
