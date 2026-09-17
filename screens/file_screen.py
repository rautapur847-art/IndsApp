import flet as ft


class FileScreen:
    """
    Generic file picker.

    Works with:
    - Web
    - Windows/Desktop
    - Android

    Callback:
        on_status(text, color)
        on_picked(path, filename, file_bytes)
    """

    def __init__(self, page: ft.Page, on_status=None, on_picked=None):

        self.page = page

        self.on_status = on_status or (
            lambda text, color="white": None
        )

        self.on_picked = on_picked or (
            lambda path, filename, file_bytes: None
        )

        self.file_picker = ft.FilePicker()

        self.page.services.append(
            self.file_picker
        )

    async def open_file_picker(self, e):

        self.on_status(
            "Opening files...",
            "blue"
        )

        try:

            files = await self.file_picker.pick_files(
                dialog_title="Select a file",

                file_type=ft.FilePickerFileType.ANY,

                allow_multiple=False,

                # Important for Web
                with_data=True,

                # Helps browser picker
                # not lose the selected file
                cancel_upload_on_window_blur=False,
            )

        except Exception as ex:

            self.on_status(
                f"File picker error: {ex}",
                "red"
            )

            return

        # User cancelled
        if not files:

            self.on_status(
                "",
                "white"
            )

            return

        picked = files[0]

        try:

            # -------------------------
            # WEB
            # -------------------------

            if picked.bytes is not None:

                file_bytes = picked.bytes
                file_path = None

            # -------------------------
            # DESKTOP / ANDROID
            # -------------------------

            elif picked.path:

                file_path = picked.path

                with open(
                    picked.path,
                    "rb"
                ) as f:
                    file_bytes = f.read()

            else:

                raise Exception(
                    "Unable to read selected file."
                )

            self.on_status(
                f"File selected: {picked.name}",
                "green"
            )

            # Send file to HomeScreen
            self.on_picked(
                file_path,
                picked.name,
                file_bytes
            )

        except Exception as ex:

            self.on_status(
                f"Error reading file: {ex}",
                "red"
            )