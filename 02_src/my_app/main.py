import flet as ft
from app.views.router import route

def main(page: ft.Page):
    page.title = "ドア開閉システム"
    

    route(page)
    page.go("/")

ft.app(target=main)