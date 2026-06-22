import os
import sys
from pathlib import Path

# Đảm bảo cwd đúng khi chạy qua preview tool
_root = Path(__file__).parent.resolve()
os.chdir(_root)
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(_root / ".env")

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))
OUTPUT_DIR.mkdir(exist_ok=True)
(OUTPUT_DIR / "videos").mkdir(exist_ok=True)
(OUTPUT_DIR / "characters").mkdir(exist_ok=True)
(OUTPUT_DIR / "products").mkdir(exist_ok=True)

app = FastAPI(title="AI Studio Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers will be added in later tasks
from api.script import router as script_router
from api.images import router as images_router
from api.batch import router as batch_router
from api.video import router as video_router
from api.characters import router as characters_router
from api.product import router as product_router
app.include_router(script_router, prefix="/api")
app.include_router(images_router, prefix="/api")
app.include_router(batch_router, prefix="/api")
app.include_router(video_router, prefix="/api")
app.include_router(characters_router, prefix="/api")
app.include_router(product_router, prefix="/api")

from fastapi import Request
from fastapi.responses import FileResponse, HTMLResponse

app.mount("/output/videos", StaticFiles(directory=str(OUTPUT_DIR / "videos")), name="videos")
app.mount("/output/characters", StaticFiles(directory=str(OUTPUT_DIR / "characters")), name="characters")
app.mount("/output/products", StaticFiles(directory=str(OUTPUT_DIR / "products")), name="products")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")

# Serve static assets (CSS, JS files nếu có)
@app.get("/")
async def serve_index():
    return FileResponse("index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

# Catch-all cho các path khác không phải /api → trả index.html
@app.get("/{full_path:path}")
async def serve_static(full_path: str, request: Request):
    from pathlib import Path as P
    file = P(full_path)
    if file.exists() and file.is_file():
        return FileResponse(full_path)
    return FileResponse("index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3456)
