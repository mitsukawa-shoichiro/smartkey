import flet as ft
import logging
import urllib.parse

logger = logging.getLogger(__name__)

def index_view(page: ft.Page, error_message: str = ""):

    def on_hover(e: ft.HoverEvent):
        btn = e.control  # イベントが起きたボタンの参照
        if e.data == "true":  # ホバー中
            btn.bgcolor = ft.Colors.LIGHT_BLUE_200
            btn.scale = 1.3
        else:  # ホバー外れ
            btn.bgcolor = ft.Colors.LIGHT_BLUE_100
            btn.scale = 1.0
        page.update()

    def logout(e):
        logger.info("ログアウトしました")
        page.go("/")

    card_btn = ft.ElevatedButton(
        content=ft.Column([
            ft.Icon(ft.Icons.CREDIT_CARD, size=50),
            ft.Text("カード管理", size=20, weight=ft.FontWeight.BOLD),
        ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        width=264,
        height=176,
        bgcolor=ft.Colors.LIGHT_BLUE_100,
        on_hover=on_hover,
        on_click=lambda e: page.go("/card"),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=20)
        )
    )

    accesslog_btn = ft.ElevatedButton(
        content=ft.Column([
            ft.Icon(ft.Icons.SENSOR_DOOR, size=50),
            ft.Text("入退出ログ", size=20, weight=ft.FontWeight.BOLD),
        ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        width=264,
        height=176,
        on_hover=on_hover,
        bgcolor=ft.Colors.LIGHT_BLUE_100,
        on_click=lambda e: page.go("/accesslogs"),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=20)
        )
    )

    add_card_btn = ft.ElevatedButton(
        content=ft.Column([
            ft.Icon(ft.Icons.ADD_CARD, size=50),
            ft.Text("カード登録", size=20, weight=ft.FontWeight.BOLD),
        ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        width=264,
        height=176,
        on_hover=on_hover,
        bgcolor=ft.Colors.LIGHT_BLUE_100,
        on_click=lambda e: page.go("/register"),
        # on_long_press=lambda e: page.go("/register/input"),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=20)
        )
    )

    upper_row = ft.Row(
        controls=[card_btn, accesslog_btn],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=60,

    )

    center_button = ft.Container(
        content=add_card_btn,
        alignment=ft.alignment.center,
        padding=ft.padding.only(top=30)
    )

    logout_button = ft.Container(
        content=ft.TextButton(
            text="ログアウト",
            icon=ft.Icons.LOGOUT,
            on_click=lambda e: logout(e),

            style=ft.ButtonStyle(
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
                shape=ft.RoundedRectangleBorder(radius=10),
                color=ft.Colors.RED,
                overlay_color=ft.Colors.RED_100,
                icon_color=ft.Colors.RED,

            )
        ),
        alignment=ft.alignment.center,
        padding=ft.padding.only(top=40)
    )

    error_text = ft.Text(
        error_message,
        color="red",
        visible=bool(error_message)
    )

    return ft.View(
        "/index",
        controls=[
            ft.Container(
                expand=True,
                alignment=ft.alignment.center,
                content=ft.Column(
                    controls=[
                        error_text,
                        ft.Container(content=ft.Text(
                            "ホーム画面", size=36, weight=ft.FontWeight.BOLD), padding=10),
                        ft.Container(content=ft.Text(
                            "ようこそ！", size=18, color=ft.Colors.BLUE_GREY_700), padding=ft.padding.only(top=4)),
                        ft.Container(height=40),
                        upper_row,
                        center_button,
                        logout_button,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                ),
            )
        ],
    )
