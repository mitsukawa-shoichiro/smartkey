import flet as ft
from app.views.router import route


def main(page: ft.Page):
    page.window_width = 800
    page.window_height = 600
    page.window_resizable = False
    page.title = "ドア開閉システム"

    route(page)
    page.go("/")


ft.app(target=main)
