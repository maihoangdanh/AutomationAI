import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))
OUTPUT_DIR.mkdir(exist_ok=True)
(OUTPUT_DIR / "videos").mkdir(exist_ok=True)

app = FastAPI(title="AI Studio Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers will be added in later tasks
from api.script import router as script_router
# from api.images import router as images_router
# from api.batch import router as batch_router
# from api.video import router as video_router
app.include_router(script_router, prefix="/api")
# app.include_router(images_router, prefix="/api")
# app.include_router(batch_router, prefix="/api")
# app.include_router(video_router, prefix="/api")

app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=3456, reload=True)
