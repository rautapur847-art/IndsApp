import flet as ft
from screens.setting import Setting


def Privacy(page: ft.Page):
    page.clean()

   

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
            "Privacy",
            weight=ft.FontWeight.BOLD,
        ),
        bgcolor=ft.Colors.WHITE_10,
    )

    def privacy_item(icon, title, description):
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        icon,
                        size=28,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(
                                title,
                                size=16,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                description,
                                size=13,
                                color=ft.Colors.GREY_400,
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                ],
                spacing=15,
            ),
            padding=15,
        )

    privacy_content = ft.Column(
        controls=[
            ft.Text(
                "Privacy & Security",
                size=25,
                weight=ft.FontWeight.BOLD,
            ),

            ft.Text(
                "Your privacy is important to us.",
                size=14,
                color=ft.Colors.GREY_400,
                text_align=ft.TextAlign.CENTER,
            ),

            ft.Divider(),

            privacy_item(
                ft.Icons.PERSON_OUTLINE,
                "Personal Information",
                "Your name, phone number and email are used "
                "to manage your IndsApp account.",
            ),

            privacy_item(
                ft.Icons.CONTACTS_OUTLINED,
                "Contacts",
                "Contacts are stored to help you communicate "
                "with people using IndsApp.",
            ),

            privacy_item(
                ft.Icons.CHAT_OUTLINED,
                "Messages",
                "Your messages are associated with the sender "
                "and receiver accounts.",
            ),

            privacy_item(
                ft.Icons.VISIBILITY_OUTLINED,
                "Online Status",
                "Your online or offline status may be visible "
                "to other users.",
            ),

            privacy_item(
                ft.Icons.LOCK_OUTLINE,
                "Account Security",
                "Keep your password private and do not share "
                "your login information with others.",
            ),

            privacy_item(
                ft.Icons.SECURITY_OUTLINED,
                "Data Protection",
                "IndsApp uses a database to store account and "
                "messaging information.",
            ),

            ft.Divider(),

            ft.Text(
                "Privacy Notice",
                size=18,
                weight=ft.FontWeight.BOLD,
            ),

            ft.Text(
                "Use IndsApp responsibly and keep your account "
                "credentials secure. Do not share sensitive "
                "personal information through chat.",
                size=14,
                color=ft.Colors.GREY_400,
                text_align=ft.TextAlign.CENTER,
            ),

            ft.Text(
                "IndsApp • Privacy & Security",
                size=12,
                color=ft.Colors.GREY_500,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
    )

    page.add(
        ft.Container(
            content=privacy_content,
            expand=True,
            padding=20,
        )
    )

    page.update()
 