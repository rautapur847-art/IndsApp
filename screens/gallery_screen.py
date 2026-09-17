import flet as ft
import base64
import io
import os
import time
from PIL import Image


class GalleryScreen:

    MAX_DIMENSION = 1280
    JPEG_QUALITY = 85

    def __init__(self, page: ft.Page, on_status=None, on_picked=None):

        self.page = page

        self.on_status = on_status or (
            lambda text, color="white": None
        )

        self.on_picked = on_picked or (
            lambda path, b64: None
        )

        self.file_picker = ft.FilePicker()

        self.page.services.append(
            self.file_picker
        )

    async def open_gallery(self, e):

        self.on_status(
            "Opening gallery...",
            "blue"
        )

        try:

            files = await self.file_picker.pick_files(
                dialog_title="Select an image",
                file_type=ft.FilePickerFileType.IMAGE,
                allow_multiple=False,
                with_data=True,
                cancel_upload_on_window_blur=False,
            )

        except Exception as ex:

            self.on_status(
                f"Gallery error: {ex}",
                "red"
            )

            return

        # User cancelled
        if not files:
            self.on_status("", "white")
            return

        picked = files[0]

        try:

            # Web
            if picked.bytes is not None:

                raw = picked.bytes

            # Desktop / Android
            elif picked.path:

                with open(
                    picked.path,
                    "rb"
                ) as f:
                    raw = f.read()

            else:

                raise Exception(
                    "Unable to read selected image."
                )

            # Resize + convert to base64
            image_path, image_b64 = (
                self._resize_and_encode(raw)
            )

            self.on_status(
                "Image selected.",
                "green"
            )

            # Send image to HomeScreen
            self.on_picked(
                image_path,
                image_b64
            )

        except Exception as ex:

            self.on_status(
                f"Error reading image: {ex}",
                "red"
            )

    def _resize_and_encode(self, raw_bytes):

        # Open image
        image = Image.open(
            io.BytesIO(raw_bytes)
        )

        # Convert PNG/WEBP/etc. to RGB
        image = image.convert("RGB")

        # Resize
        image.thumbnail(
            (
                self.MAX_DIMENSION,
                self.MAX_DIMENSION
            )
        )

        # Create assets folder
        os.makedirs(
            "assets",
            exist_ok=True
        )

        # Unique filename
        filename = (
            f"gallery_{int(time.time() * 1000)}.jpg"
        )

        image_path = os.path.join(
            "assets",
            filename
        )

        # Save JPEG
        image.save(
            image_path,
            "JPEG",
            quality=self.JPEG_QUALITY,
            optimize=True
        )

        # Read saved image
        with open(
            image_path,
            "rb"
        ) as f:
            image_bytes = f.read()

        # Base64
        image_b64 = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        return image_path, image_b64