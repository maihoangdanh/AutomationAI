import os
import asyncio
import fal_client
import httpx
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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

class CharacterRefResponse(BaseModel):
    name: str
    refs: list[dict]          # [{label, image_url, angle}]

async def _generate_one_ref(base: str, shot: dict, style: str, seed: int, char_name: str, idx: int) -> dict:
    """Generate 1 ảnh từ base_prompt + angle shot."""
    fal_key = os.getenv("FAL_KEY")
    os.environ["FAL_KEY"] = fal_key

    full_prompt = f"{base}, {shot['angle']}, {style}"

    try:
        result = await fal_client.run_async(
            "fal-ai/flux/dev",
            arguments={
                "prompt": full_prompt,
                "image_size": "square_hd",        # 1:1 cho reference sheet
                "num_inference_steps": 28,
                "guidance_scale": 3.5,
                "num_images": 1,
                "seed": seed + idx,               # seed gần nhau → face nhất quán
                "enable_safety_checker": True
            }
        )
        fal_url = result["images"][0]["url"]

        # Save locally
        filename = f"char_{char_name.lower().replace(' ','_')}_{idx}_{shot['label'].lower().replace(' ','_')}.jpg"
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
        return {
            "label": shot["label"],
            "angle": shot["angle"],
            "image_url": None,
            "error": str(e)
        }

@router.post("/character/generate-refs", response_model=CharacterRefResponse)
async def generate_character_refs(req: CharacterRefRequest):
    fal_key = os.getenv("FAL_KEY")
    if not fal_key:
        raise HTTPException(500, "FAL_KEY chưa được cấu hình trong .env")

    CHARS_DIR.mkdir(parents=True, exist_ok=True)

    # Generate 6 ảnh song song
    tasks = [
        _generate_one_ref(req.base_prompt, shot, req.style, req.seed, req.name, i)
        for i, shot in enumerate(ANGLE_SHOTS)
    ]
    results = await asyncio.gather(*tasks)

    return CharacterRefResponse(name=req.name, refs=list(results))
