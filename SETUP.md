# Setup

## 1. API Keys

Tạo file `.env` (copy từ `.env.example`):

```
GOOGLE_API_KEY=AIza...   # aistudio.google.com/apikey (free 5 video/ngày)
FAL_KEY=...               # fal.ai/dashboard (~$0.003/ảnh)
OUTPUT_DIR=./output
MAX_BATCH_PARALLEL=5
```

Anthropic (Claude): **KHÔNG cần API key** — dùng Claude Code CLI OAuth session hiện tại.

## 2. Install

```bash
pip install -r requirements.txt
```

## 3. Chạy

```bash
python server.py
```

Mở: http://localhost:3456

## 4. Test

```bash
pytest tests/ -v
```

## 5. Flow hoạt động

1. Nhập ý tưởng → chọn tỷ lệ / thời lượng / phong cách
2. Click GENERATE SCRIPT
3. Claude CLI viết kịch bản (5 scenes ~20s)
4. FAL.ai Flux generate ảnh storyboard (~30s)
5. Storyboard page: Click "🎬 Gen Video" trên từng scene → Veo 3 (~3 phút/video)
