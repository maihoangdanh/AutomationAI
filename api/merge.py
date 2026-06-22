import os
import subprocess
import tempfile
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

router = APIRouter()
OUTPUT_VIDEOS = Path(os.getenv("OUTPUT_DIR", "./output")) / "videos"

# Tìm ffmpeg: ưu tiên PATH, fallback winget install location
def _find_ffmpeg() -> str:
    import shutil
    found = shutil.which("ffmpeg")
    if found:
        return found
    winget_path = Path(os.environ.get("LOCALAPPDATA", "")) / \
        "Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    for exe in winget_path.rglob("ffmpeg.exe"):
        return str(exe)
    return "ffmpeg"

def _find_ffprobe() -> str:
    import shutil
    found = shutil.which("ffprobe")
    if found:
        return found
    winget_path = Path(os.environ.get("LOCALAPPDATA", "")) / \
        "Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    for exe in winget_path.rglob("ffprobe.exe"):
        return str(exe)
    return "ffprobe"

FFMPEG = _find_ffmpeg()
FFPROBE = _find_ffprobe()

def _check_ffmpeg():
    try:
        subprocess.run([FFMPEG, "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


@router.post("/merge-video")
async def merge_video(files: list[UploadFile] = File(...)):
    if len(files) < 2:
        raise HTTPException(400, "Cần ít nhất 2 video")
    if not _check_ffmpeg():
        raise HTTPException(500, "ffmpeg chưa được cài. Chạy: winget install ffmpeg")

    OUTPUT_VIDEOS.mkdir(parents=True, exist_ok=True)

    # Save uploaded files to temp dir
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_paths = []
        for i, f in enumerate(files):
            ext = Path(f.filename).suffix or ".mp4"
            dest = tmp_path / f"clip_{i:03d}{ext}"
            dest.write_bytes(await f.read())
            input_paths.append(dest)

        # Write concat list
        concat_txt = tmp_path / "concat.txt"
        concat_txt.write_text(
            "\n".join(f"file '{p.as_posix()}'" for p in input_paths),
            encoding="utf-8"
        )

        out_filename = f"merged_{os.urandom(4).hex()}.mp4"
        out_path = OUTPUT_VIDEOS / out_filename

        # ffmpeg concat demuxer — nhanh, không re-encode nếu cùng codec
        cmd = [
            FFMPEG, "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_txt),
            "-c", "copy",
            str(out_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            cmd_reencode = [
                FFMPEG, "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_txt),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                str(out_path)
            ]
            result2 = subprocess.run(cmd_reencode, capture_output=True, text=True)
            if result2.returncode != 0:
                raise HTTPException(502, f"ffmpeg error: {result2.stderr[-500:]}")

    size_mb = round(out_path.stat().st_size / 1024 / 1024, 1)

    duration = None
    try:
        probe = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(out_path)],
            capture_output=True, text=True
        )
        duration = round(float(probe.stdout.strip()))
    except Exception:
        pass

    return JSONResponse({
        "video_url": f"/output/videos/{out_filename}",
        "size_mb": size_mb,
        "duration": duration,
    })
