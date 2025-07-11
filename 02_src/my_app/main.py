import flet as ft
from app.views.router import route


def main(page: ft.Page):
    page.window.width = 1024
    page.window.height = 768
    page.window.resizable = False
    page.title = "ドア開閉システム"

    route(page)
    page.go("/")


ft.app(target=main)
