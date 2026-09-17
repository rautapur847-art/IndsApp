import flet as ft
from screens.setting import Setting


def Help(page: ft.Page):
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
            "Help",
            weight=ft.FontWeight.BOLD,
        ),
        bgcolor=ft.Colors.WHITE_10,
    )

    def help_item(icon, title, description):
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

    help_content = ft.Column(
        controls=[
            ft.Text(
                "How can we help you?",
                size=25,
                weight=ft.FontWeight.BOLD,
            ),

            ft.Text(
                "Find answers to common questions about IndsApp.",
                size=14,
                color=ft.Colors.GREY_400,
                text_align=ft.TextAlign.CENTER,
            ),

            ft.Divider(),

            help_item(
                ft.Icons.PERSON,
                "Account",
                "Create an account, login and manage your profile.",
            ),

            help_item(
                ft.Icons.CONTACTS,
                "Contacts",
                "Add contacts using their registered phone number.",
            ),

            help_item(
                ft.Icons.CHAT,
                "Chat",
                "Send and receive messages with your contacts.",
            ),

            help_item(
                ft.Icons.DONE_ALL,
                "Message Status",
                "Check whether your message was sent, delivered or seen.",
            ),

            help_item(
                ft.Icons.CIRCLE,
                "Online Status",
                "See whether your contacts are online or offline.",
            ),

            help_item(
                ft.Icons.SECURITY,
                "Privacy & Security",
                "Keep your account information and conversations secure.",
            ),

            ft.Divider(),

            ft.Text(
                "Still need help?",
                size=18,
                weight=ft.FontWeight.BOLD,
            ),

            ft.Text(
                "If you face any problem while using IndsApp, "
                "please contact the developer.",
                size=14,
                color=ft.Colors.GREY_400,
                text_align=ft.TextAlign.CENTER,
            ),

            ft.Text(
                "IndsApp • Help & Support",
                size=12,
                color=ft.Colors.GREY_500,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True
    )

    page.add(
        ft.Container(
            content=help_content,
            expand=True,
            padding=20,
        )
    )

    page.update()
  