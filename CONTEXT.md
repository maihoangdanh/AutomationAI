# CONTEXT — AI Studio: Video Script Architect
> Đọc file này trước khi làm bất cứ điều gì trong project.
> Claude session mới / worktree khác: đọc từ đầu đến cuối, khoảng 5 phút.
> **Cập nhật lần cuối:** 2026-06-06 — sau khi push GitHub lần đầu.

---

## 1. Project là gì và đang ở đâu

**Mục tiêu:** Web app chạy local giúp người dùng nhập ý tưởng → AI tự động tạo kịch bản video ngắn + ảnh storyboard + video clip, dùng cho TikTok / Reels / YouTube Shorts.

**Repo:** https://github.com/maihoangdanh/AutomationAI

**Chạy local tại:** `http://localhost:3456`

**Cách chạy:**
```bash
cd "D:\Quan Lieu\Automation AI"
# Kill processes cũ (Windows):
wmic process where "name='python.exe'" delete
# Chạy server:
python server.py
```

**Trạng thái tổng quan:**
- ✅ Backend FastAPI chạy được, tất cả 5 endpoints hoạt động
- ✅ Frontend luxury dark gold UI kết nối real backend
- ✅ Claude viết kịch bản thật qua CLI OAuth (không cần API key)
- ⚠️ FAL.ai: code đúng, cần nạp balance tại fal.ai/dashboard/billing
- ⚠️ Google Veo 3: code đúng, quota free hết hôm nay (reset hàng ngày), hoặc bật GCP billing
- ✅ State persist localStorage — F5 không mất data

---

## 2. Cấu trúc file — mỗi file làm gì

```
AutomationAI/
├── server.py              ← Entry point. Chạy: python server.py
├── models.py              ← Tất cả Pydantic schemas cho request/response
├── index.html             ← Toàn bộ frontend (~1950 dòng, 1 file duy nhất)
├── requirements.txt       ← pip install -r requirements.txt
├── .env                   ← API keys (gitignored, phải tạo tay)
├── .env.example           ← Template .env
├── pytest.ini             ← asyncio_mode = auto
├── api/
│   ├── __init__.py        ← Rỗng
│   ├── script.py          ← POST /api/script
│   ├── images.py          ← POST /api/image
│   ├── batch.py           ← POST /api/batch
│   ├── video.py           ← POST /api/video
│   └── characters.py      ← POST /api/character/generate-refs
├── tests/
│   ├── test_script.py
│   ├── test_images.py
│   ├── test_batch.py
│   └── test_video.py
├── output/                ← Generated files (gitignored)
│   ├── videos/            ← .mp4 từ Veo 3
│   └── characters/        ← Reference sheet images
├── README.md              ← Hướng dẫn setup cho người dùng mới
├── CONTEXT.md             ← File này
└── docs/superpowers/plans/
    └── 2026-06-06-real-ai-backend.md
```

---

## 3. File server.py — đọc kỹ vì có nhiều quirks

```python
# QUAN TRỌNG: 3 dòng đầu fix Windows cwd bug
_root = Path(__file__).parent.resolve()
os.chdir(_root)                          # phải chạy từ đúng thư mục
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))       # để import api.* được

load_dotenv(_root / ".env")              # load .env từ đúng path

# Thứ tự mount PHẢI như này (specific trước, general sau):
app.mount("/output/videos", ...)        # 1. videos
app.mount("/output/characters", ...)   # 2. characters
app.mount("/output", ...)              # 3. output root
# KHÔNG dùng app.mount("/", StaticFiles) → bắt tất cả POST → 405 Method Not Allowed

@app.get("/")                           # serve index.html
@app.get("/{full_path:path}")           # catch-all cho GET

uvicorn.run(app, ...)                   # truyền object, KHÔNG dùng string "server:app"
                                        # string mode → subprocess reload → routes không register
```

---

## 4. API Endpoints chi tiết

### POST `/api/script` — Viết kịch bản

**File:** `api/script.py`

**Request:**
```json
{
  "idea": "Quảng cáo kem trị mụn Trioderma, target gen Z 17-25",
  "aspect_ratio": "9:16",
  "duration": 30,
  "style": "viral tiktok",
  "characters": [
    {"name": "Linh", "desc": "nữ 18t tóc dài", "prompt": "Vietnamese girl, 18yo, oval face..."}
  ]
}
```

**Response:**
```json
{
  "concept": "...",
  "aspect_ratio": "9:16",
  "total_duration": 30,
  "style": "viral tiktok",
  "scenes": [
    {
      "scene_number": 1,
      "duration": 5,
      "characters": ["Linh"],
      "action": "bước vào frame nhìn thẳng camera",
      "expression": "tự tin, ánh mắt sắc",
      "camera_angle": "low angle medium shot, push in",
      "dialogue": "Bạn có biết bí mật này không?",
      "background": "studio minimalist, ánh vàng",
      "visual_description": "Vietnamese girl, 18yo..., low angle, studio, dark luxury, 8k",
      "type": "Hook — Pain Point"
    }
  ]
}
```

**Cơ chế Claude CLI (QUAN TRỌNG):**

Không dùng Anthropic SDK. Gọi qua subprocess để tận dụng OAuth session hiện tại của Claude Code CLI:

```python
# Windows: claude là .cmd file, phải dùng "cmd /c claude"
# Prompt truyền qua STDIN thay vì argument vì Vietnamese chars → UnicodeEncodeError cp1252
args = ["cmd", "/c", "claude", "-p", "-", "--output-format", "text", "--input-format", "text"]
proc = await asyncio.create_subprocess_exec(*args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
stdout, stderr = await asyncio.wait_for(proc.communicate(input=prompt.encode("utf-8")), timeout=90)
```

---

### POST `/api/image` — Generate 1 ảnh

**File:** `api/images.py`

```json
// Request
{"prompt": "Vietnamese girl, dark luxury, 8k", "aspect_ratio": "9:16", "scene_number": 1}

// Response
{"scene_number": 1, "image_url": "/output/scene_1_abc123.jpg", "prompt": "..."}
```

**FAL.ai aspect ratio mapping:**
```python
RATIO_MAP = {"9:16": "portrait_16_9", "1:1": "square", "16:9": "landscape_16_9"}
```

Model dùng: `fal-ai/flux/dev`, 28 steps, guidance 3.5

---

### POST `/api/batch` — Generate nhiều ảnh song song

**File:** `api/batch.py`

Nhận `scenes[]`, dùng `asyncio.Semaphore(5)` để giới hạn 5 concurrent FAL.ai calls.
Scene có `visual_description` rỗng → skip tự động (không crash).

```json
// Request
{"scenes": [...SceneOut objects...], "aspect_ratio": "9:16"}

// Response
{"total": 5, "completed": 5, "images": [...ImageResponse...]}
```

---

### POST `/api/video` — Generate video clip Veo 3

**File:** `api/video.py`

```json
// Request
{"prompt": "...", "aspect_ratio": "9:16", "scene_number": 1, "duration_seconds": 5}

// Response
{"scene_number": 1, "video_url": "/output/videos/scene_1_abc123.mp4", "prompt": "...", "duration_seconds": 5}
```

**QUAN TRỌNG — những thứ đã sai và đã fix:**

```python
# SAI: generate_video (singular) → AttributeError
client.models.generate_video(...)

# ĐÚNG: generate_videos (plural)
client.models.generate_videos(...)

# SAI: model name không tồn tại
model="veo-3.0-generate-preview"

# ĐÚNG: model stable
model="veo-3.0-generate-001"

# SAI: enhance_prompt không hỗ trợ → 400 INVALID_ARGUMENT
config=types.GenerateVideosConfig(enhance_prompt=True, ...)

# SAI: duration_seconds gây lỗi → 400 INVALID_ARGUMENT
config=types.GenerateVideosConfig(duration_seconds=5, ...)

# ĐÚNG: chỉ aspect_ratio + number_of_videos
config=types.GenerateVideosConfig(aspect_ratio="9:16", number_of_videos=1)
```

**Veo 3 models có sẵn:**
```
veo-2.0-generate-001        → cần billing
veo-3.0-generate-001        → stable Veo 3, ~3 phút/video ← ĐANG DÙNG
veo-3.0-fast-generate-001   → nhanh hơn
veo-3.1-generate-preview    → mới nhất
```

**Polling pattern:**
```python
operation = client.models.generate_videos(...)
while not operation.done:
    await asyncio.sleep(10)
    operation = client.operations.get(operation)
video_url = operation.response.generated_videos[0].video.uri
```

---

### POST `/api/character/generate-refs` — Reference sheet 6 góc

**File:** `api/characters.py`

```json
// Request
{
  "name": "Linh",
  "base_prompt": "Vietnamese girl, 18 years old, oval face, long black hair, slim",
  "style": "photorealistic, studio lighting, white background, 8k",
  "seed": 1234
}

// Response
{
  "name": "Linh",
  "refs": [
    {"label": "Front", "angle": "front view...", "image_url": "/output/characters/char_linh_0_front.jpg"},
    {"label": "3/4 Left", ...},
    {"label": "3/4 Right", ...},
    {"label": "Side Profile", ...},
    {"label": "Smile", ...},
    {"label": "Dynamic", ...}
  ]
}
```

6 ảnh generate song song với seed tăng dần (seed, seed+1, ..., seed+5) để face nhất quán.
Ảnh lưu tại `output/characters/char_{name}_{idx}_{label}.jpg`.

---

## 5. Frontend index.html — cấu trúc và cách hoạt động

**File duy nhất ~1950 dòng.** Không có build step, không có framework. Vanilla JS.

### State object (toàn bộ app state nằm đây)

```javascript
const state = {
  idea: '',            // ý tưởng người dùng nhập
  ratio: '9:16',       // tỷ lệ khung hình: "9:16" | "1:1" | "16:9"
  duration: 30,        // thời lượng video (giây)
  style: 'dark luxury',// phong cách video
  characters: [],      // [{name, age, desc, prompt, refs:[], avatarUrl?}]
  scenes: [],          // [{scene_number, duration, characters, action, expression, camera_angle, dialogue, background, visual_description, type}]
  activeScene: null,   // index scene đang xem trong timeline
  sbCols: 2,           // số cột storyboard grid
  imageMap: {},        // {scene_number: "/output/scene_N_xxx.jpg"}
  videoMap: {}         // {scene_number: "/output/videos/scene_N_xxx.mp4"}
};
```

### Các hàm JS quan trọng

| Hàm | Làm gì |
|-----|--------|
| `generateScript()` | async — gọi /api/script → /api/batch, update state |
| `renderTimeline()` | Render timeline bar từ state.scenes |
| `renderStoryboard()` | Render grid ảnh/video từ state.scenes + imageMap + videoMap |
| `showSceneDetail(idx)` | Hiện 8-field card của scene |
| `generateVideo(sceneIdx)` | async — gọi /api/video, update videoMap |
| `generateCharacterRefs(idx)` | async — gọi /api/character/generate-refs |
| `openAddCharacter()` | Hiện form thêm nhân vật |
| `openEditCharacter(idx)` | Hiện form edit (pre-filled) |
| `addCharacter()` | Thêm hoặc update nhân vật (dựa vào _editingIdx) |
| `saveState()` | Ghi state vào localStorage |
| `loadState()` | Đọc state từ localStorage |
| `resetAll()` | Xóa tất cả + xóa localStorage |
| `switchPage(name)` | Điều hướng giữa các trang |
| `exportJSON()` | Download state thành .json |
| `exportMarkdown()` | Download kịch bản thành .md |

### localStorage

```javascript
const STORAGE_KEY = 'aistudio_state_v1';
// Lưu: idea, ratio, duration, style, characters, scenes, imageMap, videoMap, sbCols
// Không lưu: activeScene (không cần)
```

**saveState() được gọi ở đâu:**
- `updateStatus()` — sau mọi thay đổi
- `selectPill()` — khi đổi ratio/style
- `updateDuration()` / `setDuration()` — khi đổi duration
- `oninput` trên textarea idea — mỗi keystroke

### 5 trang (tabs) trong UI

```
Ý tưởng & Cấu hình  ← nhập idea, chọn ratio/duration/style
Nhân vật             ← quản lý nhân vật, generate reference sheet
Timeline             ← xem timeline + chi tiết từng cảnh
Storyboard           ← grid ảnh/video, nút Gen Video per scene
Export & Prompts     ← JSON / Markdown / AI Prompts
```

---

## 6. .env — các keys cần thiết

```env
GOOGLE_API_KEY=AIza...      # aistudio.google.com/apikey — dùng cho Veo 3
FAL_KEY=...                  # fal.ai/dashboard/keys — dùng cho Flux images
OUTPUT_DIR=./output          # thư mục lưu output
MAX_BATCH_PARALLEL=5         # số requests FAL song song tối đa
```

**Claude/Anthropic: KHÔNG cần key.** Dùng `claude` CLI OAuth session.

---

## 7. Lịch sử bugs đã fix — biết để không làm lại

### Bug 1: 405 Method Not Allowed khi POST /api/script
**Nguyên nhân:** `app.mount("/", StaticFiles(...))` bắt tất cả requests kể cả POST.
**Fix:** Đổi sang `@app.get("/")` + `@app.get("/{full_path:path}")`. Không bao giờ dùng StaticFiles mount "/" nữa.

### Bug 2: 3 processes tranh nhau port 3456
**Nguyên nhân:** Preview tool khởi động server mới mà không kill server cũ. Curl nhận response từ server cũ (không có routes).
**Fix:** Trước khi start server mới: `wmic process where "name='python.exe'" delete`

### Bug 3: Routes empty trong `/openapi.json`
**Nguyên nhân:** `uvicorn.run("server:app", reload=True)` — uvicorn import module trong subprocess mới, cwd khác → `api.*` import fail silently.
**Fix:** `uvicorn.run(app, ...)` truyền app object trực tiếp.

### Bug 4: cwd sai khi chạy qua preview tool
**Nguyên nhân:** Preview tool chạy `python server.py` từ cwd không phải project root.
**Fix:** 3 dòng đầu server.py: `os.chdir(Path(__file__).parent.resolve())`

### Bug 5: UnicodeEncodeError khi gọi Claude CLI với tiếng Việt
**Nguyên nhân:** Windows cp1252 không encode được UTF-8. Prompt dài có tiếng Việt → crash.
**Fix:** Truyền prompt qua stdin thay vì argument: `claude -p -` + `proc.communicate(input=prompt.encode("utf-8"))`

### Bug 6: `generate_video` AttributeError (Veo 3)
**Fix:** Method đúng là `generate_videos` (plural).

### Bug 7: `enhance_prompt` + `duration_seconds` → 400 INVALID_ARGUMENT (Veo 3)
**Fix:** Remove cả hai khỏi `GenerateVideosConfig`.

### Bug 8: Model `veo-3.0-generate-preview` → 404 NOT_FOUND
**Fix:** Model đúng là `veo-3.0-generate-001`.

### Bug 9: Infinite recursion trong updateStatus()
**Nguyên nhân:** Cố patch `updateStatus` bằng function declaration mới. Do JS hoisting, `const _origUpdateStatus = updateStatus` capture chính function mới → infinite loop khi gọi.
**Fix:** Gọi `saveState()` trực tiếp trong `updateStatus()` gốc, không dùng wrapper.

### Bug 10: `openAddCharacter()` crash
**Nguyên nhân:** `document.querySelector('#add-char-panel .panel-title').childNodes[2].textContent` → undefined.
**Fix:** Xóa đoạn DOM query đó đi, chỉ giữ clear inputs + show panel.

---

## 8. Những việc CÒN LẠI (TODO)

Theo thứ tự ưu tiên:

1. **Nạp FAL.ai balance** → test image generation thật (fal.ai/dashboard/billing)
2. **Veo 3 quota** → chờ reset hàng ngày hoặc bật GCP billing
3. **Upload reference image cho nhân vật** → IP-Adapter consistency (hiện chỉ dùng text prompt)
4. **Batch video** → button "Generate tất cả videos" thay vì từng cái
5. **Ghép video** → ffmpeg concat tất cả clips thành 1 video hoàn chỉnh
6. **Multi-project** → localStorage hiện chỉ lưu 1 project. Cần project list
7. **AI Workflow tab** → hiện "sắp ra mắt"
8. **Batch Generate tab** → hiện "sắp ra mắt"
9. **Veo 3.1** → upgrade lên `veo-3.1-generate-preview` khi cần chất lượng cao hơn

---

## 9. Cách test nhanh từng endpoint

```bash
# Test script generation (cần claude CLI đã login)
curl -X POST http://localhost:3456/api/script \
  -H "Content-Type: application/json" \
  -d '{"idea":"test video","duration":15,"style":"cinematic"}'

# Test image (cần FAL_KEY có balance)
curl -X POST http://localhost:3456/api/image \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Vietnamese girl, photorealistic","aspect_ratio":"9:16","scene_number":1}'

# Test video (cần GOOGLE_API_KEY, ~3 phút)
curl -X POST http://localhost:3456/api/video \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Vietnamese girl smiling","scene_number":1}'

# Xem tất cả routes
curl http://localhost:3456/openapi.json | python -m json.tool | grep '"/'
```

---

## 10. Git workflow

```bash
# Xem lịch sử
git log --oneline

# Lấy code mới nhất
git pull

# Push thay đổi
git add -A
git commit -m "feat/fix/docs: mô tả ngắn"
git push
```

**Lưu ý:** `.env` và `output/` đã gitignore, không bao giờ được commit.

---

## 11. Khi gặp vấn đề

| Triệu chứng | Nguyên nhân | Fix |
|-------------|-------------|-----|
| `405 Method Not Allowed` | Server cũ còn chạy | `wmic process where "name='python.exe'" delete` rồi restart |
| `paths: []` trong openapi.json | uvicorn string mode hoặc cwd sai | Kiểm tra server.py dùng `uvicorn.run(app, ...)` |
| `claude CLI error` | OAuth session hết hạn | Chạy `claude` để login lại |
| `FAL_KEY chưa cấu hình` | Thiếu .env | Tạo .env từ .env.example |
| `Exhausted balance` FAL | Hết tiền | Nạp tại fal.ai/dashboard/billing |
| `RESOURCE_EXHAUSTED` Veo | Hết quota | Chờ reset hoặc bật GCP billing |
| `generate_video AttributeError` | Tên method sai | Dùng `generate_videos` (plural) |
| F5 mất data | localStorage bị clear | Kiểm tra `saveState()` được gọi sau mỗi thay đổi |
| Nút "+ Thêm nhân vật" không làm gì | JS crash trong openAddCharacter | Xem console DevTools (F12) |
