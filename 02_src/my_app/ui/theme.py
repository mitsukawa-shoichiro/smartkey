import flet as ft

BG = "#F7FAFC"
SURFACE = "#FFFFFF"
PRIMARY = "#8EC5D6"
PRIMARY_DARK = "#4F8FA3"
PINK = "#F5B8C8"
MINT = "#263238"
TEXT = "#263238"
TEXT_MUTED = "#607D8B"
DANGER = "#D86B7D"
DANGER_BG = "#FFF1F4"
BORDER = "#DDEAF0"


# 全画面共通
def apply_page_theme(page: ft.Page):
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        color_scheme = ft.ColorScheme(
            primary=PRIMARY,
            secondary=PINK,
            surface=SURFACE,
            background=BG,
            error=DANGER
        )
    )
    page.window.width = 1024
    page.window.height = 768
    page.window.min_width = 1024
    page.window.min_height = 768
