# CONTEXT — AI Studio: Video Script Architect
> File này dành cho Claude session mới / worktree khác đọc để hiểu project đang ở đâu.
> Cập nhật lần cuối: 2026-06-06

---

## Tóm tắt nhanh

**Project là gì:** Web app luxury dark gold (FastAPI backend + vanilla JS frontend) giúp người dùng nhập ý tưởng → Claude viết kịch bản video ngắn → FAL.ai generate ảnh storyboard → Google Veo 3 generate video clip. Chạy local tại `http://localhost:3456`.

**Trạng thái hiện tại:** ✅ Đang hoạt động. Backend real AI. Frontend kết nối đầy đủ. State persist localStorage.

**Repo:** https://github.com/maihoangdanh/AutomationAI

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Script AI | Claude Code CLI (`claude -p`) — OAuth session, không cần API key |
| Image AI | FAL.ai `fal-ai/flux/dev` |
| Video AI | Google Veo 3 `veo-3.0-generate-001` qua `google-genai` SDK |
| Frontend | Vanilla HTML/CSS/JS, localStorage persist |
| Port | 3456 |

---

## Cấu trúc file quan trọng

```
AutomationAI/
├── server.py              # Entry point — FastAPI app, mounts, routers
├── models.py              # Tất cả Pydantic schemas
├── index.html             # Toàn bộ frontend (1 file duy nhất, ~1900 dòng)
├── api/
│   ├── script.py          # POST /api/script — gọi claude CLI subprocess
│   ├── images.py          # POST /api/image  — fal_client.run_async
│   ├── batch.py           # POST /api/batch  — asyncio.Semaphore(5) + gather
│   ├── video.py           # POST /api/video  — genai.Client.models.generate_videos()
│   └── characters.py      # POST /api/character/generate-refs — 6 góc FAL.ai
├── .env                   # GOOGLE_API_KEY, FAL_KEY (gitignored)
├── .env.example           # Template
├── output/                # Generated files (gitignored)
│   ├── videos/            # .mp4 từ Veo 3
│   └── characters/        # Reference sheet images
└── docs/superpowers/plans/
    └── 2026-06-06-real-ai-backend.md  # Implementation plan gốc
```

---

## Lịch sử làm việc (theo thứ tự)

### Giai đoạn 1: Xây harness + UI shell
- Tạo `.claude/agents/` (script-writer, character-manager, storyboard-architect, content-optimizer)
- Tạo `.claude/skills/` (video-script-orchestrator, scene-breakdown, character-profile, storyboard-visual)
- Build `index.html` — luxury dark gold UI với 7 khu vực: Ý tưởng, Tỷ lệ, Thời lượng, Phong cách, Nhân vật, Timeline, Storyboard
- Lúc này chỉ là mock JS (generate fake scenes từ template)

### Giai đoạn 2: Backend real AI (8 tasks, subagent-driven)
- **Task 1:** FastAPI bootstrap — server.py, models.py, requirements.txt
- **Task 2:** Claude CLI proxy — `asyncio.create_subprocess_exec("claude", "-p", ...)` qua stdin để tránh Windows encoding bug
- **Task 3:** FAL.ai Flux — `fal_client.run_async("fal-ai/flux/dev", ...)`, save ảnh local
- **Task 4:** Batch parallel — `asyncio.Semaphore(MAX_BATCH_PARALLEL)` + `asyncio.gather`
- **Task 5:** Connect frontend — thay mock `generateScript()` bằng fetch `/api/script` + `/api/batch`
- **Task 6:** SETUP.md + .gitignore
- **Task 7:** Google Veo 3 — `client.models.generate_videos()`, polling `operation.done`
- **Task 8:** Video trong UI — `state.videoMap`, `generateVideo()`, `<video>` autoplay

### Giai đoạn 3: Bugs & fixes
- **Bug 1:** `405 Method Not Allowed` — do `app.mount("/", StaticFiles)` bắt tất cả POST. Fix: đổi thành `@app.get("/{full_path:path}")` route
- **Bug 2:** 3 processes tranh nhau port 3456 — server cũ không bị kill. Fix: `wmic process where "name='python.exe'" delete`
- **Bug 3:** `uvicorn.run("server:app", ...)` string mode reload → routes không register. Fix: `uvicorn.run(app, ...)` truyền object trực tiếp
- **Bug 4:** Routes empty trong openapi.json khi chạy qua preview tool — do cwd sai. Fix: `os.chdir(Path(__file__).parent)`
- **Bug 5:** Google Veo 3 SDK bugs:
  - Method tên là `generate_videos` (plural, không phải `generate_video`)
  - `enhance_prompt=True` không hỗ trợ → remove
  - Model name là `veo-3.0-generate-001` (không phải `veo-3.0-generate-preview`)
- **Bug 6:** `duration_seconds` gây lỗi 400 → remove khỏi config
- **Bug 7:** FAL.ai balance hết → cần nạp tại fal.ai/dashboard/billing

### Giai đoạn 4: Features thêm
- **Character Edit button** — nút ✎ mở form pre-filled, edit mode vs add mode
- **Character Reference Sheet** — `api/characters.py`, 6 góc song song (Front, 3/4 L, 3/4 R, Side, Smile, Dynamic), ảnh đầu làm avatar
- **localStorage persist** — `saveState()`/`loadState()`, state survive F5
  - Bug: infinite recursion khi patch `updateStatus()` bằng function declaration. Fix: gọi `saveState()` trực tiếp trong hàm gốc
  - Bug: `openAddCharacter()` crash do DOM query sai. Fix: remove đoạn query broken
- **Push GitHub** — https://github.com/maihoangdanh/AutomationAI

---

## State hiện tại của từng tính năng

| Feature | Status | Ghi chú |
|---------|--------|---------|
| Script generation (Claude) | ✅ Hoạt động | Dùng OAuth CLI, không cần API key |
| Image generation (FAL.ai) | ⚠️ Cần nạp tiền | Code đúng, chỉ thiếu balance |
| Batch generation | ✅ Code đúng | Phụ thuộc FAL balance |
| Video generation (Veo 3) | ⚠️ Quota hết hôm nay | Reset daily, hoặc bật billing |
| Character reference sheet | ✅ Code đúng | Phụ thuộc FAL balance |
| Character edit | ✅ Hoạt động | |
| localStorage persist | ✅ Hoạt động | Idea, scenes, chars, ratio, style, duration |
| Export JSON/MD/Prompts | ✅ Hoạt động | |
| GitHub sync | ✅ Đã push | maihoangdanh/AutomationAI |

---

## Cách chạy server

```bash
# Kill processes cũ nếu cần
wmic process where "name='python.exe'" delete

# Chạy
cd "D:\Quan Lieu\Automation AI"
python server.py
# → http://localhost:3456
```

**Quan trọng:** Server dùng `uvicorn.run(app, ...)` (truyền object, không phải string) và `os.chdir(Path(__file__).parent)` để fix Windows cwd issue.

---

## Các điểm kỹ thuật quan trọng cần biết

### Claude CLI subprocess (Windows)
```python
# Phải dùng stdin thay vì argument vì Vietnamese chars → UnicodeEncodeError cp1252
proc = await asyncio.create_subprocess_exec(
    "cmd", "/c", "claude", "-p", "-",  # "-" = đọc từ stdin
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)
stdout, stderr = await asyncio.wait_for(
    proc.communicate(input=prompt.encode('utf-8')), timeout=90
)
```

### FAL.ai aspect ratio mapping
```python
RATIO_MAP = {
    "9:16": "portrait_16_9",
    "1:1": "square",
    "16:9": "landscape_16_9"
}
```

### Google Veo 3 correct API
```python
operation = client.models.generate_videos(   # plural!
    model="veo-3.0-generate-001",             # stable Veo 3
    prompt=req.prompt,
    config=types.GenerateVideosConfig(        # GenerateVideosConfig (plural)
        aspect_ratio=aspect,
        number_of_videos=1,
        # KHÔNG có: enhance_prompt, duration_seconds
    )
)
```

### Mount order trong server.py (quan trọng)
```python
# Thứ tự này là bắt buộc — specific trước, general sau
app.mount("/output/videos", ...)
app.mount("/output/characters", ...)
app.mount("/output", ...)
# KHÔNG dùng app.mount("/", StaticFiles) — bắt tất cả POST → 405
@app.get("/")           # thay bằng route GET
@app.get("/{full_path:path}")
```

### localStorage keys
```javascript
const STORAGE_KEY = 'aistudio_state_v1';
const PERSIST_FIELDS = ['idea','ratio','duration','style','characters','scenes','imageMap','videoMap','sbCols'];
```

---

## Những việc CÒN LẠI / TODO

- [ ] **Upload reference image** cho nhân vật (IP-Adapter consistency)
- [ ] **Batch video** — generate tất cả scenes thành video cùng lúc, không phải từng cái
- [ ] **Export video** — ghép tất cả video clips thành 1 file hoàn chỉnh (ffmpeg)
- [ ] **Project management** — lưu nhiều project khác nhau (hiện chỉ 1 state)
- [ ] **FAL.ai balance** — cần nạp tiền để test image generation
- [ ] **Veo 3 billing** — bật GCP billing để vượt quota 5 video/ngày
- [ ] **AI Workflow tab** — hiện hiển thị "sắp ra mắt"
- [ ] **Batch Generate tab** — hiện hiển thị "sắp ra mắt"

---

## .env cần có

```env
GOOGLE_API_KEY=AIza...      # aistudio.google.com/apikey
FAL_KEY=...                  # fal.ai/dashboard/keys
OUTPUT_DIR=./output
MAX_BATCH_PARALLEL=5
```

Anthropic **KHÔNG cần** key — Claude CLI dùng OAuth hiện tại.

---

## Git log gần nhất

```
e1b4ae2  fix: openAddCharacter crash
1319c89  feat: localStorage persist - state survives F5
767b512  feat: character edit button + multi-angle reference sheet
becbc28  fix: remove duration_seconds from veo config
0591b00  fix: veo model name veo-3.0-generate-001 (stable)
2a59b5d  fix: google-genai SDK - generate_videos plural, remove enhance_prompt
18a0b0d  feat: per-scene veo 3 video generation in storyboard ui
```
