import unittest
from io import BytesIO
from unittest.mock import patch

from fastapi import HTTPException
from PIL import Image

from app.images import MAX_MODEL_EDGE, read_and_normalize_image


class FakeRequest:
    def __init__(self, body: bytes, content_type: str = "application/octet-stream"):
        self._body = body
        self.headers = {"content-length": str(len(body)), "content-type": content_type}

    async def stream(self):
        yield self._body


def image_bytes(image_format: str = "PNG", size=(20, 20)) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, "green").save(output, format=image_format)
    return output.getvalue()


def mpo_bytes(size=(20, 20), frames=2) -> bytes:
    output = BytesIO()
    images = [Image.new("RGB", size, color) for color in ("green", "orange", "blue", "red")[:frames]]
    images[0].save(output, format="MPO", save_all=True, append_images=images[1:])
    return output.getvalue()


class ImageValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_format_wins_over_request_content_type(self):
        normalized = await read_and_normalize_image(FakeRequest(image_bytes("PNG"), "text/plain"))
        with Image.open(BytesIO(normalized)) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.mode, "RGB")

    async def test_mpo_jpeg_container_is_normalized_from_first_frame(self):
        normalized = await read_and_normalize_image(FakeRequest(mpo_bytes(), "image/jpeg"))
        with Image.open(BytesIO(normalized)) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(getattr(image, "n_frames", 1), 1)
            self.assertEqual(image.getpixel((0, 0))[1] > image.getpixel((0, 0))[0], True)

    async def test_mpo_frame_limit_is_enforced(self):
        with patch("app.images.MAX_IMAGE_FRAMES", 1):
            with self.assertRaises(HTTPException) as context:
                await read_and_normalize_image(FakeRequest(mpo_bytes(frames=2)))
        self.assertIn("帧数", str(context.exception.detail))

    async def test_renamed_non_image_is_rejected(self):
        with self.assertRaises(HTTPException) as context:
            await read_and_normalize_image(FakeRequest(b"MZ-not-an-image", "image/jpeg"))
        self.assertEqual(context.exception.status_code, 400)

    async def test_pixel_limit_is_enforced_before_model_call(self):
        with patch("app.images.MAX_IMAGE_PIXELS", 100):
            with self.assertRaises(HTTPException) as context:
                await read_and_normalize_image(FakeRequest(image_bytes(size=(20, 20))))
        self.assertIn("像素", str(context.exception.detail))

    async def test_large_image_is_downscaled_for_model_latency(self):
        normalized = await read_and_normalize_image(
            FakeRequest(image_bytes(size=(1482, 1956)))
        )
        with Image.open(BytesIO(normalized)) as image:
            self.assertEqual(max(image.size), MAX_MODEL_EDGE)

    async def test_declared_oversize_is_rejected(self):
        request = FakeRequest(b"x")
        request.headers["content-length"] = str(11 * 1024 * 1024)
        with self.assertRaises(HTTPException) as context:
            await read_and_normalize_image(request)
        self.assertEqual(context.exception.status_code, 413)


if __name__ == "__main__":
    unittest.main()
