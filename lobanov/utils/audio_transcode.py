"""FFmpeg-based audio transcoding (e.g. to MP3 for APIs that only accept wav/mp3)."""

import asyncio
import shutil


class AudioTranscodeError(Exception):
    """Raised when ffmpeg is missing or transcoding fails."""


async def transcode_bytes_to_mp3(raw: bytes) -> bytes:
    """
    Convert arbitrary input audio bytes to MP3 (via ffmpeg stdin/stdout).

    Requires ``ffmpeg`` on PATH (with libmp3lame). Typical use: OpenRouter/OpenAI
    ``input_audio`` only allows ``wav`` and ``mp3`` in ``format``; m4a and others
    must be re-encoded.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        err_msg = (
            "Audio was transcoded to MP3, but `ffmpeg` was not found on PATH. "
            "Install ffmpeg, or use WAV/MP3 source files."
        )
        raise AudioTranscodeError(err_msg)
    proc = await asyncio.create_subprocess_exec(
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        "pipe:0",
        "-f",
        "mp3",
        "-acodec",
        "libmp3lame",
        "-q:a",
        "4",
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate(input=raw)
    if proc.returncode != 0:
        detail = (err or b"").decode("utf-8", errors="replace")[:4000]
        transcode_err = f"ffmpeg could not transcode to MP3 (exit {proc.returncode}): {detail}"
        raise AudioTranscodeError(transcode_err)
    if not out:
        raise AudioTranscodeError("ffmpeg produced empty MP3 output")
    return out
