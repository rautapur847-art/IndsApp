import flet as ft
import threading
import bcrypt
from database.db import Database


def LoginScreen(page: ft.Page):
    from screens.home import Home
    from screens.sign import Sign  # apna Sign-up screen jahan bhi ho

    page.clean()

    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 360
    page.window.height = 700

    message = ft.Text("", size=14)
    # value=None → indeterminate progress bar, jo khud-ba-khud
    # slider jaisa animate hota rehta hai jab tak visible=True hai
    progress = ft.ProgressBar(width=320, visible=False, value=None)

    def do_login(user_phone, user_password):
        """Ye background thread me chalta hai, taaki DB query ke
        dauraan UI freeze na ho aur progress bar animate hota rahe."""
        db = Database()
        db.cur.execute(
            "SELECT id, name, password FROM user WHERE phone = %s",
            (user_phone,),
        )
        row = db.cur.fetchone()

        progress.visible = False

        if row is None:
            message.value = "No account found with this mobile number."
            message.color = "red"
            page.update()
            return

        stored_hash = row["password"].encode()
        if not bcrypt.checkpw(user_password.encode(), stored_hash):
            message.value = "Incorrect password."
            message.color = "red"
            page.update()
            return

        message.value = "Login successful!"
        message.color = "green"
        page.update()

        Home(page, row["id"])

    def login_click(e):
        user_phone = phone.value.strip()
        user_password = password.value

        if not user_phone or not user_phone.isdigit() or len(user_phone) < 10:
            message.value = "Enter a valid 10-digit mobile number."
            message.color = "red"
            page.update()
            return

        if not user_password:
            message.value = "Enter your password."
            message.color = "red"
            page.update()
            return

        message.value = ""
        progress.visible = True
        page.update()

        # DB call ko alag thread me bhej do — UI turant responsive rehti hai
        threading.Thread(
            target=do_login, args=(user_phone, user_password), daemon=True
        ).start()

    avatar = ft.CircleAvatar(
        content=ft.Icon(ft.Icons.LOCK, size=30),
        radius=40,
        bgcolor="black",
        margin=60,
    )

    phone = ft.TextField(
        border_color="white",
        hint_text="Phone...",
        prefix_icon=ft.Icons.PHONE,
        border_radius=5,
        margin=10,
        width=320,
        keyboard_type=ft.KeyboardType.PHONE,
    )

    password = ft.TextField(
        border_color="white",
        hint_text="Password...",
        prefix_icon=ft.Icons.PASSWORD,
        password=True,
        can_reveal_password=True,
        border_radius=5,
        margin=10,
        width=320,
    )

    column = ft.Column(
        controls=[
            avatar,
            phone,
            password,
            progress,
            message,

            ft.ElevatedButton(
                "Login with IndsApp.",
                width=320,
                height=40,
                on_click=login_click,
            ),

            ft.TextButton(
                "New here? Create an account",
                on_click=lambda e: Sign(page),
            ),
        ],
        expand=True,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.HIDDEN,
    )

    page.add(column)
    page.update()