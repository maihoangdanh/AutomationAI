import pytest
from httpx import AsyncClient, ASGITransport
from server import app

MOCK_SCENES = [
    {
        "scene_number": i,
        "duration": 5,
        "characters": ["Linh"],
        "action": f"action {i}",
        "expression": "confident",
        "camera_angle": "medium shot",
        "dialogue": None,
        "background": "studio",
        "visual_description": f"Vietnamese woman, scene {i}, cinematic, 8k",
        "type": f"Scene {i}"
    }
    for i in range(1, 4)
]


@pytest.mark.asyncio
async def test_batch_returns_correct_total():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=180) as client:
        resp = await client.post("/api/batch", json={
            "scenes": MOCK_SCENES,
            "aspect_ratio": "9:16"
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert "completed" in data
    assert "images" in data


@pytest.mark.asyncio
async def test_batch_empty_prompt_skipped():
    """Scene có visual_description rỗng phải bị skip, không crash."""
    bad_scenes = MOCK_SCENES[:1] + [{
        "scene_number": 99,
        "duration": 3,
        "characters": [],
        "action": "",
        "expression": "",
        "camera_angle": "",
        "dialogue": None,
        "background": "",
        "visual_description": "",
        "type": "bad"
    }]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=180) as client:
        resp = await client.post("/api/batch", json={
            "scenes": bad_scenes,
            "aspect_ratio": "9:16"
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    # scene 99 bị skip vì prompt rỗng → completed <= total
    assert data["completed"] <= data["total"]
