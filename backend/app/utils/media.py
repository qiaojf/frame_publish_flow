import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings


class MediaToolUnavailable(RuntimeError):
    pass


@dataclass(slots=True)
class VideoMetadata:
    duration: int | None
    width: int | None
    height: int | None
    mime_type: str = "video/mp4"


class MediaProcessor:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _binary(self, configured: str, display_name: str) -> str:
        resolved = shutil.which(configured)
        if not resolved:
            raise MediaToolUnavailable(f"未找到 {display_name}，请安装 FFmpeg 并确认命令已加入 PATH")
        return resolved

    def create_mock_video(self, target: Path, duration: int = 2) -> Path:
        ffmpeg = self._binary(self.settings.ffmpeg_binary, "FFmpeg")
        target.parent.mkdir(parents=True, exist_ok=True)
        command = [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=#223a5e:s=1280x720:d={max(1, duration)}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(target),
        ]
        self._run(command, "Mock 视频生成失败")
        return target

    def probe(self, source: Path) -> VideoMetadata:
        ffprobe = self._binary(self.settings.ffprobe_binary, "ffprobe")
        command = [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height:format=duration,format_name",
            "-of",
            "json",
            str(source),
        ]
        result = self._run(command, "视频元数据读取失败", capture=True)
        payload = json.loads(result.stdout or "{}")
        streams = payload.get("streams") or [{}]
        stream = streams[0]
        duration_raw = (payload.get("format") or {}).get("duration")
        return VideoMetadata(
            duration=round(float(duration_raw)) if duration_raw else None,
            width=int(stream["width"]) if stream.get("width") else None,
            height=int(stream["height"]) if stream.get("height") else None,
        )

    def thumbnail(self, source: Path, target: Path) -> Path:
        ffmpeg = self._binary(self.settings.ffmpeg_binary, "FFmpeg")
        target.parent.mkdir(parents=True, exist_ok=True)
        command = [ffmpeg, "-y", "-ss", "0", "-i", str(source), "-frames:v", "1", "-vf", "scale=640:-1", str(target)]
        self._run(command, "视频缩略图生成失败")
        return target

    @staticmethod
    def _run(command: list[str], message: str, *, capture: bool = False) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            detail = (result.stderr or "").strip().splitlines()[-1:] or [message]
            raise RuntimeError(f"{message}: {detail[0]}")
        return result
