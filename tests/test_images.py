import pytest
from httpx import AsyncClient, ASGITransport
from server import app


@pytest.mark.asyncio
async def test_generate_image_returns_url():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=60) as client:
        resp = await client.post("/api/image", json={
            "prompt": "Vietnamese woman, confident pose, dark luxury, cinematic, 8k",
            "aspect_ratio": "9:16",
            "scene_number": 1
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "image_url" in data
    assert data["scene_number"] == 1


@pytest.mark.asyncio
async def test_generate_image_saves_locally():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=60) as client:
        resp = await client.post("/api/image", json={
            "prompt": "product photography, white tshirt, clean background, photorealistic",
            "aspect_ratio": "1:1",
            "scene_number": 2
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "scene_2" in data["image_url"]
