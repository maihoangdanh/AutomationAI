# AI Studio — Video Script Architect

> Biến 1 ý tưởng → Kịch bản chuyên nghiệp + Storyboard + Ảnh AI + Video Veo 3

![AI Studio](https://img.shields.io/badge/AI%20Studio-Video%20Script-C9A84C?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?style=flat-square)

---

## Tính năng

- **Script AI** — Claude tự động phân tích ý tưởng → kịch bản N cảnh với 8 trường chi tiết mỗi cảnh
- **Storyboard** — FAL.ai Flux generate ảnh thumbnail cho từng cảnh
- **Video Veo 3** — Google Veo 3 generate video clip per scene (click 1 nút)
- **Character Sheet** — Tạo 6 ảnh nhân vật từ nhiều góc cạnh để đảm bảo nhất quán
- **Batch Generation** — Generate 100–1000 ảnh song song (semaphore 5)
- **Auto-save** — Toàn bộ state lưu localStorage, F5 không mất data
- **Export** — JSON, Markdown, AI Prompts sẵn sàng dùng cho automation

---

## Yêu cầu

| Thứ | Phiên bản |
|-----|-----------|
| Python | 3.11+ |
| Claude Code CLI | Mới nhất (đã login) |
| FAL.ai account | fal.ai/dashboard |
| Google AI Studio | aistudio.google.com |

---

## Cài đặt

### 1. Clone repo

```bash
git clone https://github.com/maihoangdanh/AutomationAI.git
cd AutomationAI
```

### 2. Cài dependencies

```bash
pip install -r requirements.txt
```

### 3. Tạo file `.env`

```bash
cp .env.example .env
```

Mở `.env` và điền vào:

```env
GOOGLE_API_KEY=AIza...      # Lấy tại: aistudio.google.com/apikey
FAL_KEY=...                  # Lấy tại: fal.ai/dashboard/keys
OUTPUT_DIR=./output
MAX_BATCH_PARALLEL=5
```

> **Anthropic/Claude**: KHÔNG cần API key riêng — dùng Claude Code CLI OAuth

### 4. Login Claude Code (lần đầu)

```bash
claude
```

Làm theo hướng dẫn đăng nhập. Sau khi login xong có thể Ctrl+C thoát ra.

### 5. Chạy server

```bash
python server.py
```

Mở trình duyệt: **http://localhost:3456**

---

## Hướng dẫn sử dụng

### Tạo kịch bản video

1. Vào tab **Ý tưởng & Cấu hình**
2. Nhập ý tưởng vào ô text (càng chi tiết càng tốt)
3. Chọn **Tỷ lệ khung hình**: 9:16 (TikTok), 1:1 (Reels), 16:9 (Shorts)
4. Chọn **Thời lượng**: 15s / 30s / 45s / 60s
5. Chọn **Phong cách**: Dark Luxury, Viral TikTok, Cinematic...
6. Click **⚡ GENERATE SCRIPT**

Claude sẽ viết kịch bản → FAL.ai generate ảnh storyboard tự động.

### Thêm nhân vật

1. Vào tab **Nhân vật** → **+ Thêm nhân vật**
2. Điền tên, tuổi, mô tả ngoại hình
3. Thêm **Base Prompt AI** (tiếng Anh) để tăng độ nhất quán
4. Click **✦ Generate Reference Sheet** → tạo 6 ảnh từ 6 góc khác nhau
5. Ảnh đầu tiên tự động làm avatar nhân vật

### Generate Video (Veo 3)

1. Vào tab **Storyboard**
2. Đảm bảo đã có `GOOGLE_API_KEY` trong `.env`
3. Click **🎬 Gen Video (~3 phút)** trên từng cảnh
4. Veo 3 generate video → hiển thị autoplay trong card

### Export

Vào tab **Export & Prompts**:
- **JSON** — Toàn bộ kịch bản + prompts, dùng cho automation
- **Markdown** — Dễ đọc, dùng để chia sẻ
- **AI Prompts** — Danh sách prompts từng cảnh cho Midjourney/Flux/Kling

---

## Cấu trúc project

```
AutomationAI/
├── server.py              # FastAPI backend (port 3456)
├── models.py              # Pydantic schemas
├── index.html             # Frontend (luxury dark gold UI)
├── requirements.txt
├── .env.example
├── api/
│   ├── script.py          # POST /api/script — Claude CLI viết kịch bản
│   ├── images.py          # POST /api/image  — FAL.ai Flux generate ảnh
│   ├── batch.py           # POST /api/batch  — Batch parallel generate
│   ├── video.py           # POST /api/video  — Google Veo 3 generate video
│   └── characters.py      # POST /api/character/generate-refs
├── output/                # Ảnh + video generated (gitignored)
│   ├── videos/
│   └── characters/
└── docs/
    └── superpowers/plans/ # Implementation plans
```

---

## API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/script` | Viết kịch bản từ ý tưởng |
| POST | `/api/image` | Generate 1 ảnh (FAL.ai Flux) |
| POST | `/api/batch` | Generate nhiều ảnh song song |
| POST | `/api/video` | Generate video clip (Veo 3) |
| POST | `/api/character/generate-refs` | Generate reference sheet 6 góc |

### Ví dụ gọi API

```bash
# Tạo kịch bản
curl -X POST http://localhost:3456/api/script \
  -H "Content-Type: application/json" \
  -d '{
    "idea": "Quảng cáo kem trị mụn Trioderma, target gen Z 17-25",
    "aspect_ratio": "9:16",
    "duration": 30,
    "style": "viral tiktok"
  }'
```

---

## Giá API ước tính

| Service | Giá | Ghi chú |
|---------|-----|---------|
| Claude (script) | ~$0.01/kịch bản | Qua CLI OAuth — không tính phí riêng |
| FAL.ai Flux (ảnh) | ~$0.003/ảnh | Nạp min $5 |
| Google Veo 3 (video) | ~$0.35/video | Free 5 video/ngày, cần billing cho nhiều hơn |

---

## Đồng bộ giữa các máy

**Trước khi nghỉ:**
```bash
git add -A && git commit -m "wip: save" && git push
```

**Khi bắt đầu ở máy mới:**
```bash
git pull
python server.py
```

> **Lưu ý:** `.env`, `output/` không sync qua git. Cần tạo lại `.env` trên mỗi máy.

---

## Troubleshooting

**"Method Not Allowed" khi generate:**
→ Server cũ còn chạy. Mở Task Manager, kill tất cả `python.exe`, chạy lại `python server.py`

**"claude CLI error":**
→ Chạy `claude` để login lại OAuth

**"FAL_KEY chưa được cấu hình":**
→ Kiểm tra file `.env` có `FAL_KEY=...` chưa, restart server

**"RESOURCE_EXHAUSTED" (Veo 3):**
→ Hết quota free (5 video/ngày). Chờ reset hoặc bật billing tại console.cloud.google.com

**"Exhausted balance" (FAL.ai):**
→ Nạp tiền tại fal.ai/dashboard/billing

---

## License

MIT
