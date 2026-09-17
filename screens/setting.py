import flet as ft 
def Setting(page:ft.Page):
    page.clean()
    from screens.home import Home
    from screens.sign import Sign
    from screens.about import About
    from screens.help import Help
    from screens.privacy import Privacy
    page.theme_mode =ft.ThemeMode.DARK
    page.navigation_bar = None
    appbar = ft.AppBar(
        ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            tooltip="Chats",
            bgcolor=ft.Colors.BLACK_26,
            icon_size=18,
            padding=5,
            margin=5,
            on_click=lambda e: Home(page,1)
            
        ),
        title=ft.Text("setting",  weight=ft.FontWeight.BOLD,),
         
    )
    column = ft.Column(
        controls=[
            ft.ListTile(
                leading=ft.Icon(ft.Icons.HELP, color="blue"),
                title=ft.Text("Help & Supports", color="white", weight=ft.FontWeight.BOLD),
                subtitle=ft.Text("IndsApp Supports", color=ft.Colors.WHITE_54),
                trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ft.Colors.WHITE_54),
                on_click =lambda e:Help(page)
            ),
            ft.Divider(),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.PRIVACY_TIP, color="yellow"),
                title=ft.Text("Privacy.", color="white", weight=ft.FontWeight.BOLD),
                subtitle=ft.Text("IndsApp Privacy", color=ft.Colors.WHITE_54),
                trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ft.Colors.WHITE_54),
                on_click =lambda e:Privacy(page)
            ),
            ft.Divider(),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.INFO, color="green"),
                title=ft.Text("About.", color="white", weight=ft.FontWeight.BOLD),
                subtitle=ft.Text("IndsApp About", color=ft.Colors.WHITE_54),
                trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ft.Colors.WHITE_54),
                on_click =lambda e:About(page)
            ),
            ft.Divider(),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.LOGOUT, color="red"),
                title=ft.Text("Logout.", color="white", weight=ft.FontWeight.BOLD),
                subtitle=ft.Text("IndsApp Logout", color=ft.Colors.WHITE_54),
                trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ft.Colors.WHITE_54),
                on_click=lambda e: Sign(page)
            ),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True
    )
    page.appbar = appbar
    page.add(column)
    page.update()  