import flet as ft
import flet_camera as fc
import base64
import os
import time


class CameraScreen:
    """
    Live camera popup — now backed by flet-camera, which accesses the
    camera on the USER'S OWN device (via the browser/OS), not the server.
    This is what makes it actually work on a hosted --web deployment,
    where the server itself obviously has no physical camera.

      - on_status(text, color): called to update a status message
      - on_captured(image_path, b64_jpeg): called once a photo is captured
    """

    def __init__(self, page: ft.Page, on_status=None, on_captured=None):
        self.page = page
        self.on_status = on_status or (lambda text, color="white": None)
        self.on_captured = on_captured or (lambda path, b64: None)
        self.selected_camera = None
        self.is_initialized = False

        self.preview = fc.Camera(
            width=280,
            height=210,
            preview_enabled=True,
            content=ft.Container(
                alignment=ft.Alignment(0, 0),
                content=ft.Icon(ft.Icons.CAMERA_ALT, color=ft.Colors.WHITE_70, size=48),
            ),
        )

        self.dialog_status = ft.Text("Starting camera...", size=12, color=ft.Colors.WHITE_70)

        self.capture_button = ft.ElevatedButton(
            "Capture",
            icon=ft.Icons.CAMERA_ALT,
            bgcolor=ft.Colors.BLUE,
            color=ft.Colors.WHITE,
            on_click=self.capture_photo,
            disabled=True,
        )

        self.camera_dialog = ft.AlertDialog(
            title=ft.Text("Live Camera", size=16, weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [
                    self.preview,
                    self.dialog_status,
                    ft.Container(
                        content=self.capture_button,
                        alignment=ft.Alignment(0, 0),
                        margin=10,
                    ),
                ],
                tight=True,
                width=300,
            ),
            on_dismiss=self.on_dialog_close,
        )

    async def open_camera(self, e):
        self.on_status("Opening camera...", "blue")
        self.dialog_status.value = "Starting camera..."
        self.dialog_status.color = ft.Colors.WHITE_70
        self.capture_button.disabled = True

        # Open the dialog FIRST — the Camera control only becomes usable
        # once it's actually mounted in the page tree, so calling its
        # async methods before the dialog is shown would fail.
        try:
            self.page.show_dialog(self.camera_dialog)
        except Exception as ex:
            self.on_status(f"Couldn't open camera popup: {ex}", "red")
            return
        self.page.update()

        try:
            cameras = await self.preview.get_available_cameras()
        except Exception as ex:
            self.dialog_status.value = f"Camera error: {ex}"
            self.dialog_status.color = ft.Colors.RED_300
            self.page.update()
            return

        if not cameras:
            # On web, this means the browser denied/has no camera access
            # (not "no server camera" anymore, since this runs client-side).
            self.dialog_status.value = "No camera found — check browser permissions."
            self.dialog_status.color = ft.Colors.RED_300
            self.page.update()
            return

        # Prefer a back-facing camera (more useful on phones); fall back
        # to whatever's first (typical on laptops/desktops).
        self.selected_camera = next(
            (c for c in cameras if c.lens_direction == fc.CameraLensDirection.BACK),
            cameras[0],
        )

        try:
            await self.preview.initialize(
                description=self.selected_camera,
                resolution_preset=fc.ResolutionPreset.MEDIUM,
                enable_audio=False,
                image_format_group=fc.ImageFormatGroup.JPEG,
            )
        except Exception as ex:
            self.dialog_status.value = f"Couldn't start camera: {ex}"
            self.dialog_status.color = ft.Colors.RED_300
            self.page.update()
            return

        self.is_initialized = True
        self.dialog_status.value = "Camera ready"
        self.dialog_status.color = ft.Colors.WHITE_70
        self.capture_button.disabled = False
        self.page.update()

    async def capture_photo(self, e):
        if not self.is_initialized:
            self.dialog_status.value = "Camera is not ready yet."
            self.dialog_status.color = ft.Colors.RED_300
            self.page.update()
            return

        try:
            data = await self.preview.take_picture()  # raw JPEG bytes
            b64_jpeg = base64.b64encode(data).decode("utf-8")

            os.makedirs("assets", exist_ok=True)
            img_path = os.path.join("assets", f"captured_{int(time.time())}.jpg")
            with open(img_path, "wb") as f:
                f.write(data)

            self.close_camera_popup()
            self.on_captured(img_path, b64_jpeg)
        except Exception as ex:
            self.dialog_status.value = f"Capture error: {ex}"
            self.dialog_status.color = ft.Colors.RED_300
            self.page.update()

    def close_camera_popup(self):
        self.is_initialized = False
        try:
            if self.camera_dialog.open:
                self.page.pop_dialog()
            else:
                self.page.update()
        except Exception as ex:
            print(f"CameraScreen.close_camera_popup: {ex}")

    def on_dialog_close(self, e):
        # Fires if the user dismisses the popup by tapping outside it.
        self.is_initialized = False
