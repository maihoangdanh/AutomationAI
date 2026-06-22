from pydantic import BaseModel
from typing import Optional


class ProductInfo(BaseModel):
    name: str = ""
    desc: str = ""
    imageUrl: Optional[str] = None


class ScriptRequest(BaseModel):
    idea: str
    aspect_ratio: str = "9:16"
    duration: int = 30
    style: str = "dark luxury"
    characters: list[dict] = []
    product: Optional[ProductInfo] = None


class SceneOut(BaseModel):
    scene_number: int
    duration: int
    characters: list[str]
    action: str
    expression: str
    camera_angle: str
    dialogue: Optional[str]
    background: str
    visual_description: str
    type: str


class ScriptResponse(BaseModel):
    concept: str
    aspect_ratio: str
    total_duration: int
    style: str
    scenes: list[SceneOut]


class ImageRequest(BaseModel):
    prompt: str
    aspect_ratio: str = "9:16"
    scene_number: int = 1
    product_image_url: Optional[str] = None      # reference sản phẩm
    character_image_url: Optional[str] = None    # ref nhân vật (scene đầu tiên)
    prev_scene_image_url: Optional[str] = None   # ảnh cảnh trước (scene 2+, continuity)


class ImageResponse(BaseModel):
    scene_number: int
    image_url: str
    prompt: str


class BatchRequest(BaseModel):
    scenes: list[SceneOut]
    aspect_ratio: str = "9:16"
    product_image_url: Optional[str] = None  # truyền xuống từng scene


class BatchResponse(BaseModel):
    total: int
    completed: int
    images: list[ImageResponse]


class VideoRequest(BaseModel):
    prompt: str
    aspect_ratio: str = "9:16"
    scene_number: int = 1
    duration_seconds: int = 5
    reference_image_url: Optional[str] = None
    provider: str = "google"       # "google" | "fal"
    model: str = "veo-3.0-generate-001"


class VideoResponse(BaseModel):
    scene_number: int
    video_url: str
    prompt: str
    duration_seconds: int
