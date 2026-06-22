import os
import asyncio
from fastapi import APIRouter
from models import BatchRequest, BatchResponse, ImageRequest, ImageResponse, SceneOut
from api.images import generate_image

router = APIRouter()

MAX_PARALLEL = int(os.getenv("MAX_BATCH_PARALLEL", "5"))


async def _generate_one(scene: SceneOut, aspect_ratio: str,
                        product_image_url: str = None) -> ImageResponse | None:
    if not scene.visual_description.strip():
        return None
    try:
        req = ImageRequest(
            prompt=scene.visual_description,
            aspect_ratio=aspect_ratio,
            scene_number=scene.scene_number,
            product_image_url=product_image_url,
        )
        return await generate_image(req)
    except Exception:
        return None


@router.post("/batch", response_model=BatchResponse)
async def batch_generate(req: BatchRequest):
    semaphore = asyncio.Semaphore(MAX_PARALLEL)

    async def _limited(scene: SceneOut):
        async with semaphore:
            return await _generate_one(scene, req.aspect_ratio, req.product_image_url)

    results = await asyncio.gather(*[_limited(s) for s in req.scenes])
    images = [r for r in results if r is not None]

    return BatchResponse(
        total=len(req.scenes),
        completed=len(images),
        images=images
    )
