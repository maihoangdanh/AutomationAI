import pytest
from httpx import AsyncClient, ASGITransport
from server import app


@pytest.mark.asyncio
async def test_generate_video_returns_url():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=300) as client:
        resp = await client.post("/api/video", json={
            "prompt": "Vietnamese woman walking confidently on city street, dark luxury aesthetic, cinematic 9:16, slow motion",
            "aspect_ratio": "9:16",
            "scene_number": 1,
            "duration_seconds": 5
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "video_url" in data
    assert data["scene_number"] == 1
    assert data["duration_seconds"] == 5
