import flet as ft
import logging

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

    face_recognition_btn = ft.ElevatedButton(
        content=ft.Column([
            ft.Icon(ft.Icons.PERSON_SEARCH, size=50),
            ft.Text("顔認証管理", size=20, weight=ft.FontWeight.BOLD),
        ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        width=264,
        height=176,
        on_hover=on_hover,
        bgcolor=ft.Colors.LIGHT_BLUE_100,
        on_click=lambda e: page.go("/face"),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=20)
        )
    )

    face_register_btn = ft.ElevatedButton(
            content=ft.Column([
                ft.Icon(ft.Icons.FACE, size=50),
                ft.Text("顔登録", size=20, weight=ft.FontWeight.BOLD),
            ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=264,
            height=176,
            on_hover=on_hover,
            bgcolor=ft.Colors.LIGHT_BLUE_100,
            on_click=lambda e: page.go("/face_register"),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=20)
            )
        )

    camera_register_button = ft.ElevatedButton(
        content=ft.Column([
            ft.Icon(ft.Icons.SETTINGS, size=50),
            ft.Text("設備登録", size=20, weight=ft.FontWeight.BOLD),
        ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        width=264,
        height=176,
        on_hover=on_hover,
        bgcolor=ft.Colors.LIGHT_BLUE_100,
        on_click=lambda e: page.go("/user"),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=20)
        )
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
        value=error_message,
        size=16,
        color=ft.Colors.RED,
        weight=ft.FontWeight.BOLD,
        visible=bool(error_message),
        text_align=ft.TextAlign.CENTER,
    )


    middle_col = ft.Column(
        controls=[accesslog_btn],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=60,
    )

    middle_block = ft.Row(
        controls=[
            # 左
            ft.Column(
                controls=[
                    add_card_btn,
                    face_register_btn,
                ],
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            # 中
            ft.Column(
                controls=[
                    middle_col,
                    camera_register_button,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),# 右
            # 右
            ft.Column(
                controls=[
                    card_btn,
                    face_recognition_btn,
                ],
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=40,
    )

    return ft.View(
        "/index",
        controls=[
            ft.Container(
                expand=True,
                alignment=ft.alignment.center,
                content=ft.Column(
                    controls=[
                        # 上
                        ft.Column(
                            controls=[
                                ft.Container(ft.Text("ホーム画面", size=36, weight=ft.FontWeight.BOLD), padding=10),
                                ft.Container(ft.Text("ようこそ！", size=18, color=ft.Colors.BLUE_GREY_700),
                                                padding=ft.padding.only(top=4)),
                                error_text,
                                ft.Container(height=40),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        # 中
                        ft.Column(
                            controls=[
                            middle_block
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=20,
                        ),
                        # 下
                        ft.Column(
                            controls=[logout_button],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    expand=True,
                    tight=True,
                ),
            )
        ],
    )
