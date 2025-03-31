import logging
from typing import Optional, Type

import httpx
from epyxid import XID
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from skills.heurist.base import HeuristBaseTool
from utils.s3 import store_image

logger = logging.getLogger(__name__)


class ImageGenerationArthemyRealInput(BaseModel):
    """Input for ImageGenerationArthemyReal tool."""

    prompt: str = Field(
        description="Text prompt describing the image to generate.",
    )
    neg_prompt: Optional[str] = Field(
        default=None,
        description="Negative prompt describing what to avoid in the generated image.",
    )
    width: int = Field(
        default=1024,
        le=1024,
        description="Width of the generated image.",
    )
    height: int = Field(
        default=1024,
        le=1024,
        description="Height of the generated image.",
    )


class ImageGenerationArthemyReal(HeuristBaseTool):
    """Tool for generating realistic images using Heurist AI's ArthemyReal model.

    This tool takes a text prompt and uses Heurist's API to generate
    a realistic image based on the description.

    Attributes:
        name: The name of the tool.
        description: A description of what the tool does.
        args_schema: The schema for the tool's input arguments.
    """

    name: str = "heurist_image_generation_arthemy_real"
    description: str = (
        "Generate realistic images using Heurist AI's ArthemyReal model.\n"
        "Provide a text prompt describing the realistic image you want to generate.\n"
        "ArthemyReal specializes in creating photorealistic, lifelike images with fine details.\n"
        "If you have height and width, remember to specify them.\n"
    )
    args_schema: Type[BaseModel] = ImageGenerationArthemyRealInput

    async def _arun(
        self,
        prompt: str,
        neg_prompt: Optional[str] = "(worst quality: 1.4), bad quality, nsfw",
        width: int = 1024,
        height: int = 680,
        config: RunnableConfig = None,
        **kwargs,
    ) -> str:
        """Implementation of the tool to generate realistic images using Heurist AI's ArthemyReal model.

        Args:
            prompt: Text prompt describing the image to generate.
            neg_prompt: Negative prompt describing what to avoid in the generated image.
            width: Width of the generated image.
            height: Height of the generated image.
            config: Configuration for the runnable.

        Returns:
            str: URL of the generated image.
        """
        context = self.context_from_config(config)
        logger.debug(f"context: {context}")

        # Get the Heurist API key from the skill store
        api_key = self.skill_store.get_system_config("heurist_api_key")

        # Generate a unique job ID
        job_id = str(XID())

        # Prepare the request payload
        payload = {
            "job_id": job_id,
            "model_input": {
                "SD": {
                    "prompt": prompt,
                    "neg_prompt": neg_prompt,
                    "num_iterations": 25,
                    "width": width,
                    "height": height,
                    "guidance_scale": 5,
                    "seed": -1,
                }
            },
            "model_id": "ArthemyReal",
            "deadline": 120,
            "priority": 1,
        }
        logger.debug(f"Heurist API payload: {payload}")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            # Make the API request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://sequencer.heurist.xyz/submit_job",
                    json=payload,
                    headers=headers,
                    timeout=120,
                )
                logger.debug(f"Heurist API response: {response.text}")
                response.raise_for_status()

            # Store the image URL
            image_url = response.text.strip('"')
            # Generate a key with agent ID as prefix
            image_key = f"{context.agent.id}/heurist/{job_id}"
            # Store the image and get the CDN URL
            stored_url = await store_image(image_url, image_key)

            # Return the stored image URL
            return stored_url

        except httpx.HTTPStatusError as e:
            # Extract error details from response
            try:
                error_json = e.response.json()
                error_code = error_json.get("error", "")
                error_message = error_json.get("message", "")
                full_error = f"Heurist API error: Error code: {error_code}, Message: {error_message}"
            except Exception:
                full_error = f"Heurist API error: {e}"

            logger.error(full_error)
            raise Exception(full_error)

        except Exception as e:
            logger.error(f"Error generating image with Heurist: {e}")
            raise Exception(f"Error generating image with Heurist: {str(e)}")
