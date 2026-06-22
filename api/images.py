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

PRODUCT_KEYWORDS = [
    "product", "tube", "bottle", "jar", "serum", "cream", "gel", "lotion",
    "packaging", "brand", "logo", "label", "closeup product", "holding product",
    "apply", "skincare", "acne gel", "anti acne",
    "sản phẩm", "tuýp", "chai", "hộp", "kem",
]


def _is_product_scene(prompt: str) -> bool:
    low = prompt.lower()
    return any(kw in low for kw in PRODUCT_KEYWORDS)


def _resolve_url(path: str) -> str:
    """Chuyển relative path → absolute URL để FAL.ai có thể fetch."""
    if not path:
        return path
    if path.startswith("/"):
        base = os.getenv("BASE_URL", "http://localhost:3456")
        return f"{base}{path}"
    return path


async def _download_image(url: str, dest: Path) -> None:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)


async def _gen_standard(prompt: str, image_size: str) -> dict:
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


async def _gen_with_reference(prompt: str, image_size: str, reference_url: str) -> dict:
    """Gen ảnh dùng reference image qua flux-pro/v1/redux.
    Giữ được visual identity (khuôn mặt / không gian / SP) ~70-80%.
    """
    return await fal_client.run_async(
        "fal-ai/flux-pro/v1/redux",
        arguments={
            "image_url": reference_url,
            "prompt": prompt,
            "image_size": image_size,
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
            "num_images": 1,
        }
    )


@router.post("/image", response_model=ImageResponse)
async def generate_image(req: ImageRequest):
    if not os.getenv("FAL_KEY"):
        raise HTTPException(500, "FAL_KEY chưa được cấu hình trong .env")

    image_size = RATIO_MAP.get(req.aspect_ratio, "portrait_16_9")

    # ── Priority logic ──────────────────────────────────────────
    # 1. prev_scene_image_url  → continuity không gian + nhân vật từ cảnh trước
    # 2. character_image_url   → lock khuôn mặt nhân vật (scene đầu tiên)
    # 3. product_image_url     → chỉ dùng cho cảnh có SP
    # 4. None                  → gen thường từ prompt
    reference_url = None
    ref_type = "standard"

    if req.prev_scene_image_url:
        reference_url = _resolve_url(req.prev_scene_image_url)
        ref_type = "prev_scene"
    elif req.character_image_url:
        reference_url = _resolve_url(req.character_image_url)
        ref_type = "character"
    elif req.product_image_url and _is_product_scene(req.prompt):
        reference_url = _resolve_url(req.product_image_url)
        ref_type = "product"

    print(f"[IMAGE] scene={req.scene_number}  ref={ref_type}  url={reference_url or 'none'}", flush=True)

    try:
        if reference_url:
            result = await _gen_with_reference(req.prompt, image_size, reference_url)
        else:
            result = await _gen_standard(req.prompt, image_size)
    except Exception as e:
        if reference_url:
            # Fallback về standard nếu redux fail
            print(f"[IMAGE] redux failed ({e}), fallback to standard", flush=True)
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
