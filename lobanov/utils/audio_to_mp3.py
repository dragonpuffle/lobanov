"""FFmpeg-based conversion of arbitrary input audio to MP3 for storage and APIs."""

import asyncio
import shutil
import subprocess


class AudioToMp3Error(Exception):
    """Raised when ffmpeg is missing or MP3 conversion fails."""


def _convert_bytes_to_mp3_sync(raw: bytes) -> bytes:
    """Run ffmpeg via synchronous subprocess (works on Windows with any asyncio loop)."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        err_msg = "ffmpeg was not found on PATH; install ffmpeg to upload non-mp3 audio."
        raise AudioToMp3Error(err_msg)
    # Args are static; `ffmpeg` path comes from shutil.which.
    proc = subprocess.run(  # noqa: S603
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            "pipe:0",
            "-vn",
            "-map_metadata",
            "-1",
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "128k",
            "-f",
            "mp3",
            "pipe:1",
        ],
        input=raw,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or b"").decode("utf-8", errors="replace")[:4000]
        transcode_err = f"ffmpeg could not convert to MP3 (exit {proc.returncode}): {detail}"
        raise AudioToMp3Error(transcode_err)
    out = proc.stdout
    if not out:
        raise AudioToMp3Error("ffmpeg produced empty MP3 output")
    return out


async def convert_bytes_to_mp3(raw: bytes) -> bytes:
    """
    Decode arbitrary input (m4a, mp3, wav, …) to MP3 (128 kbps CBR via libmp3lame).

    Preserves source sample rate and channel layout (no -ar / -ac).

    Uses :func:`asyncio.to_thread` with a sync subprocess so conversion works on
    Windows under uvicorn, where ``SelectorEventLoop`` does not support
    :func:`asyncio.create_subprocess_exec` (``NotImplementedError``).
    """
    return await asyncio.to_thread(_convert_bytes_to_mp3_sync, raw)
