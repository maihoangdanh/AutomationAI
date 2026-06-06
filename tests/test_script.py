import pytest
from httpx import AsyncClient, ASGITransport
from server import app


@pytest.mark.asyncio
async def test_generate_script_returns_scenes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=60) as client:
        resp = await client.post("/api/script", json={
            "idea": "quảng cáo áo thun nữ phong cách urban",
            "aspect_ratio": "9:16",
            "duration": 30,
            "style": "dark luxury",
            "characters": []
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "scenes" in data
    assert len(data["scenes"]) >= 3
    scene = data["scenes"][0]
    for field in ["scene_number", "duration", "action", "expression",
                  "camera_angle", "background", "visual_description", "type"]:
        assert field in scene, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_script_scene_visual_description_not_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=60) as client:
        resp = await client.post("/api/script", json={
            "idea": "review son môi cao cấp",
            "duration": 15,
            "style": "cinematic"
        })
    data = resp.json()
    for scene in data["scenes"]:
        assert len(scene["visual_description"]) > 20
