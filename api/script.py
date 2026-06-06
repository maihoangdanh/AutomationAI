import asyncio
import json
from fastapi import APIRouter, HTTPException
from models import ScriptRequest, ScriptResponse, SceneOut

router = APIRouter()

SYSTEM_PROMPT = """Bạn là chuyên gia viết kịch bản video ngắn viral cho TikTok, Reels, YouTube Shorts.
Nhiệm vụ: Nhận ý tưởng → trả về JSON kịch bản phân cảnh chuyên nghiệp.

QUAN TRỌNG: Chỉ trả về JSON thuần túy, không có text thêm, không có markdown code block.

Format JSON bắt buộc:
{
  "concept": "tóm tắt concept ngắn",
  "total_duration": <số giây>,
  "aspect_ratio": "<tỷ lệ>",
  "style": "<phong cách>",
  "scenes": [
    {
      "scene_number": 1,
      "duration": <số giây 2-8>,
      "characters": ["tên nhân vật"],
      "action": "hành động cụ thể động từ mạnh",
      "expression": "biểu cảm khuôn mặt và body language",
      "camera_angle": "loại shot + góc + movement",
      "dialogue": "lời thoại hoặc null",
      "background": "môi trường + ánh sáng",
      "visual_description": "AI image/video prompt đầy đủ dưới 100 từ tiếng Anh",
      "type": "tên cảnh ngắn gọn"
    }
  ]
}

Quy tắc:
- Scene đầu: hook mạnh (shock, câu hỏi, FOMO)
- Scene cuối: CTA rõ ràng
- visual_description phải là prompt tiếng Anh, thêm: cinematic, photorealistic, 8k
- Số scene: 15s→3, 30s→5, 45s→7, 60s→9
- Chỉ trả JSON, không giải thích thêm"""


def _build_prompt(req: ScriptRequest) -> str:
    chars = ", ".join(c.get("name", "") for c in req.characters) if req.characters else "nhân vật chính (nữ, Vietnamese)"
    char_detail = "\n".join(
        f"- {c['name']}: {c.get('desc', '')} | base_prompt: {c.get('prompt', 'Vietnamese woman, photorealistic')}"
        for c in req.characters
    ) if req.characters else ""
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Ý tưởng: {req.idea}\n"
        f"Tỷ lệ: {req.aspect_ratio}\n"
        f"Thời lượng: {req.duration}s\n"
        f"Phong cách: {req.style}\n"
        f"Nhân vật: {chars}\n"
        f"{char_detail}\n\n"
        f"Tạo kịch bản phân cảnh hoàn chỉnh. Chỉ trả về JSON."
    )


async def _call_claude_cli(prompt: str) -> str:
    """Gọi claude CLI subprocess, dùng OAuth session hiện tại."""
    import sys

    # On Windows, claude is a .cmd file; pass prompt via stdin to avoid encoding issues
    if sys.platform == "win32":
        args = ["cmd", "/c", "claude", "-p", "-",
                "--output-format", "text",
                "--input-format", "text"]
    else:
        args = ["claude", "-p", "-",
                "--output-format", "text",
                "--input-format", "text"]

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    prompt_bytes = prompt.encode("utf-8")
    stdout, stderr = await asyncio.wait_for(
        proc.communicate(input=prompt_bytes), timeout=90
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI error: {stderr.decode('utf-8', errors='replace')}")
    return stdout.decode("utf-8", errors="replace").strip()


@router.post("/script", response_model=ScriptResponse)
async def generate_script(req: ScriptRequest):
    if not req.idea.strip():
        raise HTTPException(400, "idea không được để trống")

    try:
        raw = await _call_claude_cli(_build_prompt(req))
    except asyncio.TimeoutError:
        raise HTTPException(504, "Claude CLI timeout — thử lại")
    except RuntimeError as e:
        raise HTTPException(500, str(e))

    # Bỏ code fences nếu Claude vẫn wrap
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            stripped = part.lstrip("json").strip()
            if stripped.startswith("{"):
                raw = stripped
                break

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"Claude trả về JSON không hợp lệ: {e}\nRaw: {raw[:200]}")

    scenes = [
        SceneOut(
            scene_number=s.get("scene_number", i),
            duration=s.get("duration", 5),
            characters=s.get("characters", ["nhân vật chính"]),
            action=s.get("action", ""),
            expression=s.get("expression", ""),
            camera_angle=s.get("camera_angle", "medium shot"),
            dialogue=s.get("dialogue"),
            background=s.get("background", ""),
            visual_description=s.get("visual_description", ""),
            type=s.get("type", f"Scene {i}")
        )
        for i, s in enumerate(data.get("scenes", []), 1)
    ]

    return ScriptResponse(
        concept=data.get("concept", req.idea),
        aspect_ratio=req.aspect_ratio,
        total_duration=req.duration,
        style=req.style,
        scenes=scenes
    )
