from __future__ import annotations

import warnings
from io import BytesIO

from fastapi import HTTPException, Request
from PIL import Image, ImageOps, UnidentifiedImageError


MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
MAX_IMAGE_FRAMES = 4
MAX_MODEL_EDGE = 1280
SUPPORTED_FORMATS = {"JPEG", "MPO", "PNG", "WEBP"}


def _has_expected_signature(body: bytes | bytearray, image_format: str) -> bool:
    if image_format in {"JPEG", "MPO"}:
        return body.startswith(b"\xff\xd8\xff")
    if image_format == "PNG":
        return body.startswith(b"\x89PNG\r\n\x1a\n")
    if image_format == "WEBP":
        return len(body) >= 12 and body[:4] == b"RIFF" and body[8:12] == b"WEBP"
    return False


async def read_and_normalize_image(request: Request) -> bytes:
    declared_length = request.headers.get("content-length")
    if declared_length:
        try:
            if int(declared_length) > MAX_UPLOAD_SIZE_BYTES:
                raise HTTPException(status_code=413, detail="图片大小不能超过 10 MiB")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Content-Length 无效") from exc

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="图片大小不能超过 10 MiB")
        body.extend(chunk)
    if not body:
        raise HTTPException(status_code=400, detail="图片内容不能为空")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(body)) as probe:
                # Extension and Content-Type are attacker-controlled; Pillow's
                # decoded format must also agree with the real file signature.
                image_format = (probe.format or "").upper()
                if image_format not in SUPPORTED_FORMATS:
                    detected = image_format or "未知格式"
                    raise HTTPException(
                        status_code=400,
                        detail=f"检测到 {detected}；仅支持真实的 JPEG、PNG 或 WebP 图片",
                    )
                if not _has_expected_signature(body, image_format):
                    raise HTTPException(status_code=400, detail="图片格式标识与真实文件头不一致")

                frame_count = getattr(probe, "n_frames", 1)
                if frame_count < 1 or frame_count > MAX_IMAGE_FRAMES:
                    raise HTTPException(status_code=400, detail="图片帧数无效或过多")
                total_pixels = 0
                for frame_index in range(frame_count):
                    probe.seek(frame_index)
                    width, height = probe.size
                    if width <= 0 or height <= 0:
                        raise HTTPException(status_code=400, detail="图片像素尺寸无效")
                    total_pixels += width * height
                    if total_pixels > MAX_IMAGE_PIXELS:
                        raise HTTPException(status_code=400, detail="图片总像素超过 4000 万像素")
                probe.seek(0)
                probe.verify()

            with Image.open(BytesIO(body)) as source:
                source.seek(0)
                source.load()
                normalized = ImageOps.exif_transpose(source).convert("RGB")
                normalized.thumbnail((MAX_MODEL_EDGE, MAX_MODEL_EDGE), Image.Resampling.LANCZOS)
                output = BytesIO()
                normalized.save(output, format="JPEG", quality=88, optimize=True)
                return output.getvalue()
    except HTTPException:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=400, detail="文件内容不是完整、有效的图片") from exc
