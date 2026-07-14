import flet as ft
from ui import theme


def page_title(title: str, subtitle: str | None = None):
    """各画面のタイトル"""
    controls = [
        ft.Text(title, size=30, weight=ft.FontWeight.BOLD, color=theme.TEXT)
    ]
    if subtitle:
        controls.append(ft.Text(subtitle, size=13, color=theme.TEXT_MUTED))
    return ft.Column(controls, spacing=4)

def soft_panel(content, width=None, padding=24):
    """検索欄やフォームに使う"""
    return ft.Container(
        content=content,
        width=width,
        padding=padding,
        bgcolor=theme.SURFACE,
        border=ft.border.all(1, theme.BORDER),
        border_radius=14,
        shadow=ft.BoxShadow(
            blur_radius=18,
            spread_radius=0,
            color="#22000000",
            offset=ft.Offset(0, 6),
        ),
    )

def primary_button(text: str, icon=None, on_click=None, width=None):
    """通常の主要ボタン。登録・検索・保存など"""
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        width=width,
        style=ft.ButtonStyle(
            bgcolor=theme.PRIMARY,
            color=ft.Colors.WHITE,
            icon_color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=18, vertical=12),
        ),
    )

def ghost_button(text: str, icon=None, on_click=None, width=None):
    """戻る・キャンセルなど"""
    return ft.OutlinedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        width=width,
        style=ft.ButtonStyle(
            color=theme.PRIMARY_DARK,
            icon_color=theme.PRIMARY_DARK,
            side=ft.BorderSide(1, theme.BORDER),
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=18, vertical=12),
        ),
    )

def danger_button(text: str, icon=None, on_click=None, width=None):
    """削除・停止など"""
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        width=width,
        style=ft.ButtonStyle(
            bgcolor=theme.DANGER_BG,
            color=theme.DANGER,
            icon_color=theme.DANGER,
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=18, vertical=12),
        ),
    )

def text_field(label: str, width=320, password=False, autofocus=False, on_submit=None):
    """入力欄の統一"""
    return ft.TextField(
        label=label,
        width=width,
        password=password,
        autofocus=autofocus,
        on_submit=on_submit,
        border_radius=10,
        border_color=theme.BORDER,
        focused_border_color=theme.PRIMARY,
        cursor_color=theme.PRIMARY_DARK,
    )

def feature_tile(icon, title: str, subtitle: str, accent: str, on_click):
    """ホーム画面の機能タイル"""
    return ft.Container(
        width=260,
        height=150,
        padding=20,
        bgcolor=theme.SURFACE,
        border=ft.border.all(1, theme.BORDER),
        border_radius=16,
        shadow=ft.BoxShadow(
            blur_radius=16,
            color="#18000000",
            offset=ft.Offset(0, 5),
        ),
        ink=True,
        on_click=on_click,
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Icon(icon, size=30, color=accent),
                    width=48,
                    height=48,
                    border_radius=14,
                    bgcolor=f"{accent}22",
                    alignment=ft.alignment.center,
                ),
                ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=theme.TEXT),
                ft.Text(subtitle, size=12, color=theme.TEXT_MUTED),
            ],
            spacing=10,
        ),
    )

def view_shell(route: str, title: str, subtitle: str, body, back_to="/index"):
    """一覧・登録画面"""
    return ft.View(
        route,
        controls=[
            ft.Container(
                expand=True,
                padding=ft.padding.symmetric(horizontal=56, vertical=32),
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                page_title(title, subtitle),
                                ghost_button("戻る", ft.Icons.ARROW_BACK, lambda e: e.page.go(back_to)),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Container(height=18),
                        body,
                    ],
                    expand=True,
                ),
            )
        ],
    )
