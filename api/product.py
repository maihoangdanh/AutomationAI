import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File

router = APIRouter()
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))
PRODUCT_DIR = OUTPUT_DIR / "products"


@router.post("/product/upload-image")
async def upload_product_image(file: UploadFile = File(...)):
    PRODUCT_DIR.mkdir(parents=True, exist_ok=True)
    ext = (file.filename or "image.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        ext = "jpg"
    filename = f"product_{os.urandom(4).hex()}.{ext}"
    (PRODUCT_DIR / filename).write_bytes(await file.read())
    return {"image_url": f"/output/products/{filename}"}
