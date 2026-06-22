import os
import asyncio
import fal_client
import httpx
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from google import genai
from google.genai import types as gtypes

router = APIRouter()
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))
CHARS_DIR = OUTPUT_DIR / "characters"

# 6 góc chuẩn cho reference sheet
ANGLE_SHOTS = [
    {"label": "Front",       "angle": "front view, looking straight at camera, neutral expression"},
    {"label": "3/4 Left",    "angle": "3/4 angle left, slight turn, natural expression"},
    {"label": "3/4 Right",   "angle": "3/4 angle right, slight turn, confident expression"},
    {"label": "Side Profile","angle": "side profile view, looking left, clean jawline visible"},
    {"label": "Smile",       "angle": "front view, warm genuine smile, eyes slightly squinted"},
    {"label": "Dynamic",     "angle": "slight downward angle, looking up at camera, powerful pose"},
]

class CharacterRefRequest(BaseModel):
    name: str
    base_prompt: str          # VD: "Vietnamese girl, 18, oval face, long black hair"
    style: str = "photorealistic, studio lighting, white background, 8k, sharp focus"
    seed: int = 42            # Cùng seed → nhất quán khuôn mặt
    provider: str = "fal"    # "fal" | "google"
    model: str = "fal-ai/flux/dev"

class CharacterRefResponse(BaseModel):
    name: str
    refs: list[dict]          # [{label, image_url, angle}]

class RetryRefRequest(BaseModel):
    name: str
    base_prompt: str
    style: str = "photorealistic, studio lighting, white background, 8k, sharp focus"
    seed: int = 42            # Phải dùng đúng seed gốc để face nhất quán
    angle_idx: int            # 0–5, index trong ANGLE_SHOTS
    provider: str = "fal"
    model: str = "fal-ai/flux/dev"


async def _gen_fal(full_prompt: str, model: str, seed: int, idx: int, char_name: str, shot: dict) -> dict:
    """Generate 1 ảnh qua FAL.ai."""
    try:
        result = await fal_client.run_async(
            model,
            arguments={
                "prompt": full_prompt,
                "image_size": "square_hd",
                "num_inference_steps": 28,
                "guidance_scale": 3.5,
                "num_images": 1,
                "seed": seed + idx,
                "enable_safety_checker": True
            }
        )
        fal_url = result["images"][0]["url"]

        safe_label = shot['label'].lower().replace(' ','_').replace('/','_')
        filename = f"char_{char_name.lower().replace(' ','_')}_{idx}_{safe_label}.jpg"
        local_path = CHARS_DIR / filename
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(fal_url)
            resp.raise_for_status()
            local_path.write_bytes(resp.content)

        return {
            "label": shot["label"],
            "angle": shot["angle"],
            "image_url": f"/output/characters/{filename}"
        }
    except Exception as e:
        return {"label": shot["label"], "angle": shot["angle"], "image_url": None, "error": str(e)}


async def _gen_imagen(full_prompt: str, model: str, seed: int, idx: int, char_name: str, shot: dict) -> dict:
    """Generate 1 ảnh qua Google Imagen / Gemini Image."""
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY chưa được cấu hình trong .env")

        client = genai.Client(api_key=api_key)
        response = client.models.generate_images(
            model=model,
            prompt=full_prompt,
            config=gtypes.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="1:1",
            )
        )
        img_data = response.generated_images[0].image.image_bytes

        safe_label = shot['label'].lower().replace(' ','_').replace('/','_')
        filename = f"char_{char_name.lower().replace(' ','_')}_{idx}_{safe_label}.jpg"
        local_path = CHARS_DIR / filename
        local_path.write_bytes(img_data)

        return {
            "label": shot["label"],
            "angle": shot["angle"],
            "image_url": f"/output/characters/{filename}"
        }
    except Exception as e:
        return {"label": shot["label"], "angle": shot["angle"], "image_url": None, "error": str(e)}


async def _generate_one_ref(base: str, shot: dict, style: str, seed: int, char_name: str, idx: int,
                             provider: str = "fal", model: str = "fal-ai/flux/dev") -> dict:
    """Generate 1 ảnh từ base_prompt + angle shot, chọn provider."""
    full_prompt = f"{base}, {shot['angle']}, {style}"

    if provider == "google":
        return await _gen_imagen(full_prompt, model, seed, idx, char_name, shot)
    else:
        return await _gen_fal(full_prompt, model, seed, idx, char_name, shot)


@router.post("/character/retry-ref")
async def retry_character_ref(req: RetryRefRequest):
    """Retry 1 ảnh lỗi, dùng đúng seed gốc để giữ nhất quán khuôn mặt."""
    if req.provider == "fal":
        if not os.getenv("FAL_KEY"):
            raise HTTPException(500, "FAL_KEY chưa được cấu hình trong .env")
    elif req.provider == "google":
        if not os.getenv("GOOGLE_API_KEY"):
            raise HTTPException(500, "GOOGLE_API_KEY chưa được cấu hình trong .env")

    if req.angle_idx < 0 or req.angle_idx >= len(ANGLE_SHOTS):
        raise HTTPException(400, f"angle_idx phải từ 0 đến {len(ANGLE_SHOTS)-1}")

    CHARS_DIR.mkdir(parents=True, exist_ok=True)
    shot = ANGLE_SHOTS[req.angle_idx]
    result = await _generate_one_ref(
        req.base_prompt, shot, req.style, req.seed, req.name, req.angle_idx,
        provider=req.provider, model=req.model
    )
    return result


@router.post("/character/upload-ref")
async def upload_character_ref(
    file: UploadFile = File(...),
    char_name: str = Form(...),
    angle_idx: int = Form(...),
):
    """Upload ảnh thủ công cho 1 slot trong reference sheet."""
    if angle_idx < 0 or angle_idx >= len(ANGLE_SHOTS):
        raise HTTPException(400, f"angle_idx phải từ 0 đến {len(ANGLE_SHOTS)-1}")

    CHARS_DIR.mkdir(parents=True, exist_ok=True)
    shot = ANGLE_SHOTS[angle_idx]
    safe_label = shot['label'].lower().replace(' ', '_').replace('/', '_')
    ext = (file.filename or "image.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        ext = "jpg"
    filename = f"char_{char_name.lower().replace(' ','_')}_{angle_idx}_{safe_label}.{ext}"
    local_path = CHARS_DIR / filename
    local_path.write_bytes(await file.read())

    return {
        "label": shot["label"],
        "angle": shot["angle"],
        "image_url": f"/output/characters/{filename}"
    }


@router.post("/character/generate-refs", response_model=CharacterRefResponse)
async def generate_character_refs(req: CharacterRefRequest):
    if req.provider == "fal":
        fal_key = os.getenv("FAL_KEY")
        if not fal_key:
            raise HTTPException(500, "FAL_KEY chưa được cấu hình trong .env")
    elif req.provider == "google":
        if not os.getenv("GOOGLE_API_KEY"):
            raise HTTPException(500, "GOOGLE_API_KEY chưa được cấu hình trong .env")

    CHARS_DIR.mkdir(parents=True, exist_ok=True)

    # Generate 6 ảnh song song
    tasks = [
        _generate_one_ref(req.base_prompt, shot, req.style, req.seed, req.name, i,
                          provider=req.provider, model=req.model)
        for i, shot in enumerate(ANGLE_SHOTS)
    ]
    results = await asyncio.gather(*tasks)

    return CharacterRefResponse(name=req.name, refs=list(results))
