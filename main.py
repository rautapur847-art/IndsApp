# ----------------- App entry  point -------------------
import flet as ft
from screens.login import LoginScreen

def main(page:ft.Page):
    page.clean()
    page.window.width = 360
    page.window.height = 700
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    LoginScreen(page)
   
ft.run(main, view=ft.AppView.WEB_BROWSER,assets_dir="assets")