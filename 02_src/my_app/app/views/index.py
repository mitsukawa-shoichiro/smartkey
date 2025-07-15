import flet as ft
import requests


def index_view(page: ft.Page):

    card_btn = ft.ElevatedButton(
        content=ft.Column([
            ft.Icon(ft.Icons.CREDIT_CARD, size=50),
            ft.Text("カード管理", size=20, weight=ft.FontWeight.BOLD),
        ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        width=264,
        height=176,
        bgcolor=ft.Colors.LIGHT_BLUE_50,
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
        bgcolor=ft.Colors.LIGHT_BLUE_50,
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
        bgcolor=ft.Colors.LIGHT_BLUE_50,
        on_click=lambda e: page.go("/register"),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=20)
        )
    )

    uopper_row = ft.Row(
        controls=[card_btn, accesslog_btn],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=60,
    )

    center_button = ft.Container(
        content=add_card_btn,
        alignment=ft.alignment.center,
        padding=ft.padding.only(top=30)
    )
    SESAME_ID = "11200413-0002-0611-3F00-9200FFFFFFFF"
    API_KEY = "O3R8DiaBCR2CD8mi10ibR9yT5OMqZHByaDmSCmnT"

    def get_battery():
        url = f"https://app.candyhouse.co/api/sesame2/{SESAME_ID}"
        headers = {"x-api-key": API_KEY}
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return int(resp.json().get("batteryPercentage", -1))
    
    
    try:
        battery = get_battery()
    except Exception as e:
        battery = None
        print("取得エラー:", e)
       
    if 80 <= battery <= 100:
        battery_icon = ft.Icon(ft.Icons.BATTERY_FULL, size=24, color=ft.Colors.GREEN)
        battery_text = ft.Text(f"{battery}%", size=16, color=ft.Colors.BLUE_GREY_700)
    elif 50 < battery < 80:
        battery_icon = ft.Icon(ft.Icons.BATTERY_5_BAR, size=24, color=ft.Colors.GREEN)
        battery_text = ft.Text(f"{battery}%", size=16, color=ft.Colors.BLUE_GREY_700)
    elif 20 < battery <= 50:
        battery_icon = ft.Icon(ft.Icons.BATTERY_3_BAR, size=24, color=ft.Colors.ORANGE)
        battery_text = ft.Text(f"{battery}%", size=16, color=ft.Colors.BLUE_GREY_700)
    elif battery <= 20:
        battery_icon = ft.Icon(ft.Icons.BATTERY_1_BAR, size=24, color=ft.Colors.RED)
        battery_text = ft.Text(f"{battery}%", size=16, color=ft.Colors.BLUE_GREY_700)
        
    battery_card = ft.Card(
        content=ft.Container(
            width=200, 
            padding=10,
            content=ft.Column(
                controls=[
                    ft.Text("sesameバッテリー残量", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        controls=[battery_icon, battery_text],
                        spacing=10,
                        alignment=ft.MainAxisAlignment.START
                    )
                ],
            spacing=10,
            )
        ),
        elevation=2,
    )
    
    logout_button = ft.Container(
        content=ft.TextButton(
            text="ログアウト",
            icon=ft.Icons.LOGOUT,
            on_click=lambda e: page.go("/"),
            style=ft.ButtonStyle(
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
                shape=ft.RoundedRectangleBorder(radius=10),

            )
        ),
        alignment=ft.alignment.center,
        padding=ft.padding.only(top=40)
    )
    return ft.View(
        "/index",
        controls=[
            ft.Row(
                controls=[
                    battery_card 
                ],
                alignment=ft.MainAxisAlignment.START,  
                vertical_alignment=ft.CrossAxisAlignment.START,  
            ),

            ft.Container(
                expand=True,
                alignment=ft.alignment.center,
                content=ft.Column(
                    controls=[
                        ft.Container(content=ft.Text(
                            "ホーム画面", size=36, weight=ft.FontWeight.BOLD), padding=10),
                        ft.Container(content=ft.Text(
                            "ようこそ！", size=18, color=ft.Colors.BLUE_GREY_700), padding=ft.padding.only(top=4)),
                        ft.Container(height=40),
                        uopper_row,
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
