import os
import httpx
import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException
from google import genai
from google.genai import types
from models import VideoRequest, VideoResponse

router = APIRouter()
OUTPUT_VIDEOS = Path(os.getenv("OUTPUT_DIR", "./output")) / "videos"

RATIO_MAP = {
    "9:16": "9:16",
    "16:9": "16:9",
    "1:1": "1:1"
}


async def _download_video(url: str, dest: Path) -> None:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)


@router.post("/video", response_model=VideoResponse)
async def generate_video(req: VideoRequest):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(500, "GOOGLE_API_KEY chưa được cấu hình trong .env")

    client = genai.Client(api_key=api_key)
    aspect = RATIO_MAP.get(req.aspect_ratio, "9:16")

    try:
        operation = client.models.generate_video(
            model="veo-3.0-generate-preview",
            prompt=req.prompt,
            config=types.GenerateVideoConfig(
                aspect_ratio=aspect,
                duration_seconds=req.duration_seconds,
                number_of_videos=1,
                enhance_prompt=True,
            )
        )

        while not operation.done:
            await asyncio.sleep(10)
            operation = client.operations.get(operation)

        if operation.error:
            raise HTTPException(502, f"Veo 3 error: {operation.error.message}")

        video = operation.response.generated_videos[0]
        veo_url = video.video.uri

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Google Veo 3 error: {e}")

    filename = f"scene_{req.scene_number}_{os.urandom(4).hex()}.mp4"
    local_path = OUTPUT_VIDEOS / filename
    await _download_video(veo_url, local_path)

    return VideoResponse(
        scene_number=req.scene_number,
        video_url=f"/output/videos/{filename}",
        prompt=req.prompt,
        duration_seconds=req.duration_seconds
    )
