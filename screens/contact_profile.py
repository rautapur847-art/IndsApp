import flet as ft


def get_initials(full_name):
    words = full_name.strip().split()
    if not words:
        return "?"
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return words[0][0].upper()


def ContactProfile(page: ft.Page, my_id: int, contact_id: int, contact_name: str, contact_phone: str):
    page.clean()
    from screens.chat import Chat
    from screens.home import Home
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 360
    page.window.height = 700

    appbar = ft.AppBar(
        ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            tooltip="Chats",
            bgcolor=ft.Colors.BLACK_26,
            icon_size=18,
            padding=5,
            margin=5,
            on_click=lambda e: Home(page, my_id)
        ),
        title=ft.Text("Contact info"),
        bgcolor=ft.Colors.WHITE_10,
    )

    avatar = ft.CircleAvatar(
        content=ft.Text(
            get_initials(contact_name),
            size=36,
            weight=ft.FontWeight.BOLD,
        ),
        radius=50,
        bgcolor="black",
    )

    column = ft.Column(
        controls=[
            ft.Container(height=30),
            avatar,
            ft.Container(height=20),
            ft.Text(contact_name, size=22, weight=ft.FontWeight.BOLD),
            ft.Container(height=15),
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.PHONE, size=18, color="grey"),
                    ft.Text(str(contact_phone), size=16),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.START,
        expand=True,
    )

    page.appbar = appbar
    page.add(column)
    page.update()