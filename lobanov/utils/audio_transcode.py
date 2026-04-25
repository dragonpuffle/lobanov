"""FFmpeg-based transcoding to PCM WAV for OpenAI-compatible ``input_audio`` (OpenRouter STT)."""

import asyncio
import shutil
import subprocess


class AudioTranscodeError(Exception):
    """Raised when ffmpeg is missing or transcoding fails."""


def _transcode_bytes_to_wav_sync(raw: bytes) -> bytes:
    """Run ffmpeg via synchronous subprocess (works on Windows with any asyncio loop)."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        err_msg = "ffmpeg was not found on PATH. Install ffmpeg, or reconfigure STT."
        raise AudioTranscodeError(err_msg)
    # PCM 16k mono: reliable for OpenAI ``input_audio``; MP3 from disk often rejected as invalid.
    # apad: very short clips must be padded so the API min duration (~0.1s) is met.
    proc = subprocess.run(  # noqa: S603
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            "pipe:0",
            "-af",
            "apad=whole_dur=0.15",
            "-f",
            "wav",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            "pipe:1",
        ],
        input=raw,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or b"").decode("utf-8", errors="replace")[:4000]
        transcode_err = f"ffmpeg could not transcode to WAV (exit {proc.returncode}): {detail}"
        raise AudioTranscodeError(transcode_err)
    out = proc.stdout
    if not out:
        raise AudioTranscodeError("ffmpeg produced empty WAV output")
    return out


async def transcode_bytes_to_wav(raw: bytes) -> bytes:
    """
    Decode input (e.g. MP3, M4A) to 16 kHz mono PCM WAV for ``input_audio``.

    Storage may remain MP3; this path is only for the OpenRouter / OpenAI request body.

    Uses :func:`asyncio.to_thread` with a sync subprocess so transcoding works on
    Windows under uvicorn, where ``SelectorEventLoop`` does not support
    :func:`asyncio.create_subprocess_exec` (``NotImplementedError``).
    """
    return await asyncio.to_thread(_transcode_bytes_to_wav_sync, raw)
