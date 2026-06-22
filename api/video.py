import os
import httpx
import asyncio
import fal_client
from pathlib import Path
from fastapi import APIRouter, HTTPException
from google import genai
from google.genai import types
from models import VideoRequest, VideoResponse

router = APIRouter()
OUTPUT_VIDEOS = Path(os.getenv("OUTPUT_DIR", "./output")) / "videos"

RATIO_MAP = {"9:16": "9:16", "16:9": "16:9", "1:1": "1:1"}
# Kling dùng ratio string khác
KLING_RATIO_MAP = {"9:16": "9:16", "16:9": "16:9", "1:1": "1:1"}


async def _download_video(url: str, dest: Path) -> None:
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)


async def _gen_google_veo(req: VideoRequest) -> str:
    """Generate video bằng Google Veo. Trả về URL video."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(500, "GOOGLE_API_KEY chưa được cấu hình trong .env")

    client = genai.Client(api_key=api_key)
    aspect = RATIO_MAP.get(req.aspect_ratio, "9:16")

    operation = client.models.generate_videos(
        model=req.model,
        prompt=req.prompt,
        config=types.GenerateVideosConfig(
            aspect_ratio=aspect,
            number_of_videos=1,
        )
    )
    # Poll — Veo 3 mất 2–5 phút, Veo 2 nhanh hơn
    while not operation.done:
        await asyncio.sleep(10)
        operation = client.operations.get(operation)

    if operation.error:
        raise HTTPException(502, f"{req.model} error: {operation.error.message}")

    return operation.response.generated_videos[0].video.uri


async def _gen_fal_kling(req: VideoRequest) -> str:
    """Generate video bằng Kling qua FAL.ai. Trả về URL video."""
    if not os.getenv("FAL_KEY"):
        raise HTTPException(500, "FAL_KEY chưa được cấu hình trong .env")

    aspect = KLING_RATIO_MAP.get(req.aspect_ratio, "9:16")
    duration = "5" if req.duration_seconds <= 5 else "10"

    result = await fal_client.run_async(
        req.model,
        arguments={
            "prompt": req.prompt,
            "duration": duration,
            "aspect_ratio": aspect,
        }
    )
    return result["video"]["url"]


@router.post("/video", response_model=VideoResponse)
async def generate_video(req: VideoRequest):
    OUTPUT_VIDEOS.mkdir(parents=True, exist_ok=True)

    try:
        if req.provider == "fal":
            video_url = await _gen_fal_kling(req)
        else:
            video_url = await _gen_google_veo(req)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Video generation error ({req.provider}/{req.model}): {e}")

    filename = f"scene_{req.scene_number}_{os.urandom(4).hex()}.mp4"
    local_path = OUTPUT_VIDEOS / filename
    await _download_video(video_url, local_path)

    return VideoResponse(
        scene_number=req.scene_number,
        video_url=f"/output/videos/{filename}",
        prompt=req.prompt,
        duration_seconds=req.duration_seconds,
    )
