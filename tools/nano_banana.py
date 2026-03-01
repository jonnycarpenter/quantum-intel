"""
Nano Banana 2: Infographic Generation Tool
==========================================

Generates visual assets (infographics, diagrams, illustrations) using the 
Gemini Imagen3 API. Designed to support "Ad-Hoc Analysis" modals.
"""

import json
import logging
import os
import uuid
from typing import Optional

logger = logging.getLogger(__name__)


class GenerateInfographicTool:
    """Tool to generate images/infographics via Gemini Imagen 3."""

    def __init__(self):
        self._client = None
        self._output_dir = "static/generated_assets"
        os.makedirs(self._output_dir, exist_ok=True)

    def _ensure_client(self) -> None:
        """Lazy-initialize Gemini client."""
        if self._client is None:
            # Requires google-genai package
            try:
                from google import genai
                self._client = genai.Client() # Uses GOOGLE_API_KEY from environment
            except ImportError:
                logger.error("google-genai package not installed")
                raise ValueError("google-genai package not installed")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                raise ValueError(f"Failed to initialize Gemini client: {e}")

    async def execute(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        style: str = "vector_art",
    ) -> str:
        """
        Generate an infographic image.

        Args:
            prompt: Detailed description of the image to generate
            aspect_ratio: e.g., "16:9", "1:1", "4:3", "3:4", "9:16"
            style: e.g., "vector_art", "photograph", "sketch", "3d"

        Returns:
            JSON string with the generated image URL and success status
        """
        logger.info(f"[TOOL] generate_infographic: prompt='{prompt[:50]}...' style='{style}' aspect_ratio='{aspect_ratio}'")

        try:
            self._ensure_client()
        except ValueError as e:
            return json.dumps({
                "status": "error",
                "message": f"Gemini configuration error: {e}"
            })

        try:
            import asyncio
            from google.genai import types

            # Run the synchronous generate_images call in an executor thread
            # as the genai SDK might not natively support async for this specific endpoint yet
            loop = asyncio.get_event_loop()
            
            # Map 'style' to acceptable Gemini terms if needed or just append to prompt
            enhanced_prompt = f"Professional business style, {style}. {prompt}. Clean, high quality, accurate."
            
            response = await loop.run_in_executor(
                None,
                lambda: self._client.models.generate_images(
                    model='imagen-3.0-generate-002',
                    prompt=enhanced_prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        output_mime_type="image/jpeg",
                        aspect_ratio=aspect_ratio,
                        add_watermark=False,
                    )
                )
            )

            if not response.generated_images:
                return json.dumps({
                    "status": "error",
                    "message": "The model failed to generate any images."
                })

            # Save the image locally (mocking a cloud storage upload for this demo)
            image_data = response.generated_images[0].image.image_bytes
            
            # Generate a unique filename
            filename = f"infographic_{uuid.uuid4().hex[:8]}.jpeg"
            filepath = os.path.join(self._output_dir, filename)
            
            with open(filepath, "wb") as f:
                f.write(image_data)
                
            # Assume a local static file server is running, or upload to GCS in the future
            public_url = f"/api/assets/{filename}"
            
            logger.info(f"[TOOL] generate_infographic: Successfully generated image at {public_url}")

            # Return success to the agent with the markdown-ready image string
            return json.dumps({
                "status": "success",
                "message": "Successfully generated the infographic.",
                "image_url": public_url,
                "markdown": f"![Generated Infographic]({public_url})"
            })

        except Exception as e:
            logger.error(f"[TOOL] generate_infographic error: {e}")
            return json.dumps({
                "status": "error",
                "message": f"Failed to generate infographic: {type(e).__name__}: {e}"
            })
