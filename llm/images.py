"""Shared helpers for multimodal (vision) LLM requests."""

import base64
from pathlib import Path
from typing import List, Union

ImageInput = Union[bytes, str, Path]


def normalize_images(images: List[ImageInput]) -> List[bytes]:
    """Normalize paths or bytes into raw image bytes."""
    out: List[bytes] = []
    for item in images:
        if isinstance(item, bytes):
            out.append(item)
        else:
            out.append(Path(item).read_bytes())
    return out


def b64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def guess_media_type(data: bytes) -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:2] == b"\xff\xd8":
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"