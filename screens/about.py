import flet as ft
from screens.setting import Setting


def About(page: ft.Page):
    page.clean()

    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

   
    # --------------------------------
    # AppBar
    # --------------------------------
    page.appbar = ft.AppBar(
        ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            tooltip="Chats",
            bgcolor=ft.Colors.BLACK_26,
            icon_size=18,
            padding=5,
            margin=5,
              on_click=lambda e: Setting(page)
            
        ),
        
        title=ft.Text(
            "About IndsApp",
            weight=ft.FontWeight.BOLD,
        ),
        bgcolor=ft.Colors.WHITE_10,
    )

    # --------------------------------
    # IndsApp Logo
    # --------------------------------
    logo = ft.Container(
        content=ft.CircleAvatar(
            content=ft.Text(
                "I",
                size=40,
                weight=ft.FontWeight.BOLD,
            ),
            radius=55,
            bgcolor="black",
        ),
        margin=ft.Margin(0, 0, 0, 15),
    )

    # --------------------------------
    # App Name
    # --------------------------------
    app_name = ft.Text(
        "IndsApp",
        size=30,
        weight=ft.FontWeight.BOLD,
    )

    version = ft.Text(
        "Version 1.0",
        size=13,
        color=ft.Colors.GREY_400,
    )

    # --------------------------------
    # About Text
    # --------------------------------
    about_text = ft.Text(
        "IndsApp is a real-time messaging application "
        "developed using Python, Flet and MySQL.\n\n"
        "It provides a simple and user-friendly platform "
        "for communication between users.",
        size=15,
        text_align=ft.TextAlign.CENTER,
    )

    # --------------------------------
    # Features
    # --------------------------------
    features = ft.Column(
        controls=[
            ft.Text(
                "Features",
                size=20,
                weight=ft.FontWeight.BOLD,
            ),

            ft.Row(
                [
                    ft.Icon(ft.Icons.PERSON,color="blue"),
                    ft.Text("User Registration & Login"),
                ],
            ),

            ft.Row(
                [
                    ft.Icon(ft.Icons.CONTACTS,color="red"),
                    ft.Text("Add Contacts"),
                ],
            ),

            ft.Row(
                [
                    ft.Icon(ft.Icons.CHAT,color="green"),
                    ft.Text("One-to-One Chat"),
                ],
            ),

            ft.Row(
                [
                    ft.Icon(ft.Icons.PHONE,color="white"),
                    ft.Text("Phone Number Based Contacts"),
                ],
            ),

            ft.Row(
                [
                    ft.Icon(ft.Icons.CIRCLE,color="green"),
                    ft.Text("Online / Offline Status"),
                ],
            ),

            ft.Row(
                [
                    ft.Icon(ft.Icons.DONE_ALL,color="blue"),
                    ft.Text("Message Status"),
                ],
            ),
        ],
        spacing=12,
    )

    # --------------------------------
    # Technology
    # --------------------------------
    technology = ft.Column(
        controls=[
            ft.Text(
                "Technology",
                size=20,
                weight=ft.FontWeight.BOLD,
            ),

            ft.Text("Python  →  Application Logic"),
            ft.Text("Flet    →  User Interface"),
            ft.Text("MySQL   →  Database"),
        ],
        spacing=8,
    )

    # --------------------------------
    # Developer
    # --------------------------------
    developer = ft.Text(
        "Developed as a B.Tech Project",
        size=13,
        color=ft.Colors.GREY_400,
        text_align=ft.TextAlign.CENTER,
    )

    # --------------------------------
    # Main UI
    # --------------------------------
    page.add(
        ft.Column(
            controls=[
                logo,
                app_name,
                version,

                ft.Divider(),

                about_text,

                ft.Divider(),

                features,

                ft.Divider(),

                technology,

                ft.Divider(),

                developer,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15,
            expand=True,
            margin=20,
            scroll=ft.ScrollMode.AUTO
        )
    )

    page.update()
  