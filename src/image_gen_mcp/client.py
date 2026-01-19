"""Client for laozhang.ai Gemini 3 Pro image generation API."""

import base64
from typing import Any

import httpx


class ImageGenError(Exception):
    """Error from image generation API."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ImageGenClient:
    """Client for generating images via laozhang.ai Gemini 3 Pro API."""

    ENDPOINT = "https://api.laozhang.ai/v1beta/models/gemini-3-pro-image-preview:generateContent"
    TIMEOUT = 120.0  # Image generation can take a while

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.TIMEOUT)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_request_body(
        self,
        prompt: str,
        aspect_ratio: str,
        size: str,
        reference_images: list[bytes] | None = None,
    ) -> dict[str, Any]:
        """Build the API request body for image generation.

        The laozhang.ai API follows Google's Gemini content generation format.
        Image parameters (aspectRatio, imageSize) must be nested inside imageConfig.

        Note: numberOfImages does NOT work with Gemini 3 Pro Image - it only works
        with Imagen models. For multiple images, make sequential API calls.

        Args:
            prompt: Text description
            aspect_ratio: Output aspect ratio
            size: Output resolution (1K, 2K, 4K - must be uppercase)
            reference_images: Optional list of image bytes to use as style/content reference
        """
        # Build parts list - images first, then text prompt
        parts: list[dict[str, Any]] = []

        # Add reference images if provided
        if reference_images:
            for img_bytes in reference_images:
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                parts.append({
                    "inlineData": {
                        "mimeType": "image/jpeg",
                        "data": img_b64
                    }
                })

        # Add text prompt
        parts.append({"text": prompt})

        return {
            "contents": [
                {
                    "parts": parts
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": {
                    "aspectRatio": aspect_ratio,
                    "imageSize": size,
                }
            },
        }

    async def _single_generate(
        self,
        prompt: str,
        aspect_ratio: str,
        size: str,
        reference_images: list[bytes] | None = None,
    ) -> bytes:
        """Generate a single image. Internal method used by generate().

        Returns:
            Single image as bytes (JPEG format)

        Raises:
            ImageGenError: If the API request fails
        """
        client = await self._get_client()

        body = self._build_request_body(prompt, aspect_ratio, size, reference_images)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = await client.post(
                self.ENDPOINT,
                json=body,
                headers=headers,
            )
        except httpx.TimeoutException:
            raise ImageGenError("Request timed out. Try a smaller image size or simpler prompt.")
        except httpx.RequestError as e:
            raise ImageGenError(f"Network error: {e}")

        # Handle HTTP errors
        if response.status_code == 401:
            raise ImageGenError("Invalid API key", status_code=401)
        if response.status_code == 429:
            raise ImageGenError("Rate limit exceeded. Please wait before trying again.", status_code=429)
        if response.status_code >= 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)
            except Exception:
                error_msg = response.text
            raise ImageGenError(f"API error: {error_msg}", status_code=response.status_code)

        # Parse response and extract image
        try:
            data = response.json()
            images = self._extract_images(data)
            return images[0]  # API returns one image per request
        except Exception as e:
            raise ImageGenError(f"Failed to parse API response: {e}")

    async def generate(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        size: str = "2K",
        num_images: int = 1,
        reference_images: list[bytes] | None = None,
    ) -> list[bytes]:
        """Generate images from a text prompt, optionally using reference images.

        Note: Gemini 3 Pro Image only generates one image per API call.
        For multiple images, this method makes sequential requests.

        Args:
            prompt: Text description of the desired image
            aspect_ratio: Aspect ratio (1:1, 16:9, etc.)
            size: Resolution (1K, 2K, 4K)
            num_images: Number of images to generate (1-4)
            reference_images: Optional list of image bytes to use as style/content reference

        Returns:
            List of image data as bytes (JPEG format)

        Raises:
            ImageGenError: If the API request fails
        """
        images: list[bytes] = []

        for _ in range(num_images):
            image = await self._single_generate(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                size=size,
                reference_images=reference_images,
            )
            images.append(image)

        return images

    def _extract_images(self, response_data: dict[str, Any]) -> list[bytes]:
        """Extract image bytes from the API response.

        The Gemini API returns images as base64-encoded data in the response
        candidates' content parts with mimeType "image/jpeg" or similar.
        """
        images: list[bytes] = []

        candidates = response_data.get("candidates", [])
        if not candidates:
            raise ImageGenError("No candidates in API response")

        for candidate in candidates:
            content = candidate.get("content", {})
            parts = content.get("parts", [])

            for part in parts:
                # Look for inline image data
                inline_data = part.get("inlineData")
                if inline_data:
                    mime_type = inline_data.get("mimeType", "")
                    if mime_type.startswith("image/"):
                        image_b64 = inline_data.get("data", "")
                        if image_b64:
                            image_bytes = base64.b64decode(image_b64)
                            images.append(image_bytes)

        if not images:
            raise ImageGenError("No images found in API response")

        return images
