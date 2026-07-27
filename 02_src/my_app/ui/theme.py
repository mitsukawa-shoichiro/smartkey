import flet as ft


FONT_FAMILY = "Noto Sans JP"
FONT_WEIGHT = ft.FontWeight.W_900
NAV_BUTTON_SIZE = 52
NAV_ICON_SIZE = 24

BG = "#FFFFFF"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F8FBFC"

PRIMARY = "#529BC3"
PRIMARY_DARK = "#3F7F9F"

PINK = "#E36C98"
PINK_SOFT = "#FCE8F0"

SKY = "#529BC3"
SKY_SOFT = "#E5F2F8"

MINT = "#57A188"
MINT_SOFT = "#E6F3ED"

LAVENDER = "#8975B2"
LAVENDER_SOFT = "#EFEBF7"

SUN = "#D89A3D"
SUN_SOFT = "#FFF6E7"

TEXT = "#3A4C57"
TEXT_MUTED = "#79888E"

BORDER = "#DCE5E8"
BORDER_HOVER = "#C8D7DD"
ROW_HOVER = "#F8FBFC"
HEADING_BG = "#F2F7F8"

DANGER = "#D75D70"
DANGER_BG = "#FCECEF"


def apply_page_theme(page: ft.Page):
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.LIGHT

    page.theme = ft.Theme(
        font_family=FONT_FAMILY,
        use_material3=True,

        page_transitions=ft.PageTransitionsTheme(
            windows=ft.PageTransitionTheme.ZOOM,
        ),

        color_scheme=ft.ColorScheme(
            primary=PRIMARY,
            secondary=PINK,
            tertiary=MINT,
            surface=SURFACE,
            error=DANGER,
        ),
        elevated_button_theme=ft.ElevatedButtonTheme(
            bgcolor=PRIMARY,
            foreground_color="#FFFFFF",
            icon_color="#FFFFFF",
            elevation=0,
            padding=ft.padding.symmetric(
                horizontal=20,
                vertical=14,
            ),
            shape=ft.RoundedRectangleBorder(radius=8),
            text_style=ft.TextStyle(
                font_family=FONT_FAMILY,
                weight=FONT_WEIGHT,
            ),
        ),
        outlined_button_theme=ft.OutlinedButtonTheme(
            bgcolor=SURFACE,
            foreground_color=TEXT,
            icon_color=TEXT_MUTED,
            overlay_color=SKY_SOFT,
            border_side=ft.BorderSide(1, BORDER),
            padding=ft.padding.symmetric(
                horizontal=18,
                vertical=13,
            ),
            shape=ft.RoundedRectangleBorder(radius=8),
            text_style=ft.TextStyle(
                font_family=FONT_FAMILY,
                weight=FONT_WEIGHT,
            ),
        ),
        dialog_theme=ft.DialogTheme(
            bgcolor=SURFACE,
            surface_tint_color=SURFACE,
            shadow_color="#16000000",
            elevation=8,
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
        data_table_theme=ft.DataTableTheme(
            heading_row_color=HEADING_BG,
            heading_row_height=52,
            data_row_min_height=54,
            data_row_max_height=54,
            divider_thickness=1,
            heading_text_style=ft.TextStyle(
                color=TEXT,
                font_family=FONT_FAMILY,
                weight=FONT_WEIGHT,
            ),
            data_text_style=ft.TextStyle(
                color=TEXT,
                font_family=FONT_FAMILY,
                weight=FONT_WEIGHT,
            ),
        ),
        scrollbar_theme=ft.ScrollbarTheme(
            thumb_visibility=False,
            track_visibility=False,
            thickness=0,
            interactive=False,
        ),
    )

    page.window.width = 1180
    page.window.height = 820
    page.window.min_width = 1000
    page.window.min_height = 720
    page.window.resizable = True