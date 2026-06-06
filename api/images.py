import os
import httpx
import fal_client
from pathlib import Path
from fastapi import APIRouter, HTTPException
from models import ImageRequest, ImageResponse

router = APIRouter()
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))

RATIO_MAP = {
    "9:16": "portrait_16_9",
    "1:1": "square",
    "16:9": "landscape_16_9"
}


async def _download_image(url: str, dest: Path) -> None:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)


@router.post("/image", response_model=ImageResponse)
async def generate_image(req: ImageRequest):
    fal_key = os.getenv("FAL_KEY")
    if not fal_key:
        raise HTTPException(500, "FAL_KEY chưa được cấu hình trong .env")

    os.environ["FAL_KEY"] = fal_key
    image_size = RATIO_MAP.get(req.aspect_ratio, "portrait_16_9")

    try:
        result = await fal_client.run_async(
            "fal-ai/flux/dev",
            arguments={
                "prompt": req.prompt,
                "image_size": image_size,
                "num_inference_steps": 28,
                "guidance_scale": 3.5,
                "num_images": 1,
                "enable_safety_checker": True
            }
        )
    except Exception as e:
        raise HTTPException(502, f"FAL.ai error: {e}")

    fal_url = result["images"][0]["url"]

    stem = Path(fal_url.split("?")[0]).stem[:8]
    filename = f"scene_{req.scene_number}_{stem}.jpg"
    local_path = OUTPUT_DIR / filename
    await _download_image(fal_url, local_path)

    return ImageResponse(
        scene_number=req.scene_number,
        image_url=f"/output/{filename}",
        prompt=req.prompt
    )
