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

# Keywords để nhận biết cảnh có xuất hiện sản phẩm
PRODUCT_KEYWORDS = [
    "product", "tube", "bottle", "jar", "serum", "cream", "gel", "lotion",
    "packaging", "brand", "logo", "label", "closeup product", "close-up product",
    "holding product", "apply", "skincare", "acne gel", "anti acne",
    # Tiếng Việt
    "sản phẩm", "tuýp", "chai", "hộp", "kem", "serum",
]


def _is_product_scene(prompt: str) -> bool:
    """Trả về True nếu prompt mô tả cảnh có sản phẩm xuất hiện."""
    low = prompt.lower()
    return any(kw in low for kw in PRODUCT_KEYWORDS)


async def _download_image(url: str, dest: Path) -> None:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)


async def _gen_standard(prompt: str, image_size: str) -> dict:
    """Gen ảnh thường bằng Flux Dev."""
    return await fal_client.run_async(
        "fal-ai/flux/dev",
        arguments={
            "prompt": prompt,
            "image_size": image_size,
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
            "num_images": 1,
            "enable_safety_checker": True,
        }
    )


async def _gen_with_product_ref(prompt: str, image_size: str, product_image_url: str) -> dict:
    """Gen ảnh dùng ảnh SP làm reference qua flux-pro/v1/redux.
    Redux giữ được visual identity của SP (hình dáng, màu sắc, logo) ~70-80%.
    """
    # Resolve absolute URL nếu là relative path (/output/products/...)
    base_url = os.getenv("BASE_URL", "http://localhost:3456")
    if product_image_url.startswith("/"):
        product_image_url = f"{base_url}{product_image_url}"

    return await fal_client.run_async(
        "fal-ai/flux-pro/v1/redux",
        arguments={
            "image_url": product_image_url,
            "prompt": prompt,
            "image_size": image_size,
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
            "num_images": 1,
        }
    )


@router.post("/image", response_model=ImageResponse)
async def generate_image(req: ImageRequest):
    fal_key = os.getenv("FAL_KEY")
    if not fal_key:
        raise HTTPException(500, "FAL_KEY chưa được cấu hình trong .env")

    image_size = RATIO_MAP.get(req.aspect_ratio, "portrait_16_9")
    use_product_ref = (
        req.product_image_url
        and _is_product_scene(req.prompt)
    )

    try:
        if use_product_ref:
            result = await _gen_with_product_ref(req.prompt, image_size, req.product_image_url)
        else:
            result = await _gen_standard(req.prompt, image_size)
    except Exception as e:
        # Nếu redux fail (quota/key issue) → fallback về standard
        if use_product_ref:
            try:
                result = await _gen_standard(req.prompt, image_size)
            except Exception as e2:
                raise HTTPException(502, f"FAL.ai error: {e2}")
        else:
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
