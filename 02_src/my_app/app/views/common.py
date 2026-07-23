"""
GUI(Flet)の各画面で共有する共通処理をまとめるモジュール。

repository/service層は例外をraiseで投げっぱなしにする設計(層分けの原則)なので、
GUI層(view)側で必ずtry/exceptで受け止め、ユーザーに分かる形で表示する必要がある。
この受け止め方(エラーダイアログの出し方)を1箇所にまとめ、各画面から使い回す。
"""
from my_app.ui import theme as ui_theme
import flet as ft
from my_app.app.utils import japanese_text as jt

import logging
import my_app.db.repository as repo

logger = logging.getLogger(__name__)

# ===================================================
# デザイントークン(色・角丸・余白の共通定義)
# ===================================================
# 1箇所にまとめておくことで、全画面のトーンを揃え、後から一括で変えられる。
# 入退室管理という業務ツールらしい、落ち着いた信頼感のあるライトテーマ。

class Theme:
    BG = ui_theme.BG
    SURFACE = ui_theme.SURFACE
    PRIMARY = ui_theme.PRIMARY
    PRIMARY_DARK = ui_theme.PRIMARY_DARK

    PINK = ui_theme.PINK
    PINK_SOFT = ui_theme.PINK_SOFT
    SKY = ui_theme.SKY
    SKY_SOFT = ui_theme.SKY_SOFT
    MINT = ui_theme.MINT
    MINT_SOFT = ui_theme.MINT_SOFT
    LAVENDER = ui_theme.LAVENDER
    LAVENDER_SOFT = ui_theme.LAVENDER_SOFT

    MAUVE = "#A17C9F"
    MAUVE_SOFT = "#F4EBF2"

    LOG_BLUE = "#4F8FAF"
    LOG_BLUE_SOFT = "#E4F1F7"

    EQUIPMENT_GREEN = "#4F9475"
    EQUIPMENT_GREEN_SOFT = "#E4F2EA"

    SUN = "#D89A3D"
    SUN_SOFT = "#FFF6E7"

    TEXT = ui_theme.TEXT
    TEXT_MUTED = ui_theme.TEXT_MUTED
    DANGER = ui_theme.DANGER

    HEADING_BG = ui_theme.HEADING_BG
    ROW_HOVER = ui_theme.ROW_HOVER
    BORDER = ui_theme.BORDER

    RADIUS = 8
    RADIUS_SM = 8


_ROUTE_META = {
    "/management": (
        "管理",
        Theme.MINT,
        Theme.MINT_SOFT,
        ft.Icons.GRID_VIEW,
    ),
    "/card": (
        "カード管理",
        Theme.MINT,
        Theme.MINT_SOFT,
        ft.Icons.CREDIT_CARD,
    ),
    "/face": (
        "顔管理",
        Theme.LAVENDER,
        Theme.LAVENDER_SOFT,
        ft.Icons.PERSON_SEARCH,
    ),
    "/user": (
        "ユーザー管理",
        "#A17C9F",
        "#F4EBF2",
        ft.Icons.PEOPLE,
    ),
    "/access_logs": (
        "入退室ログ",
        "#4F8FAF",
        "#E4F1F7",
        ft.Icons.SENSOR_DOOR,
    ),
    "/face_register": (
        "顔登録",
        Theme.LAVENDER,
        Theme.LAVENDER_SOFT,
        ft.Icons.ADD_A_PHOTO,
    ),
    "/face_register/input": (
        "本人情報",
        Theme.LAVENDER,
        Theme.LAVENDER_SOFT,
        ft.Icons.PERSON_ADD,
    ),
    "/register": (
        "カード登録",
        Theme.SKY,
        Theme.SKY_SOFT,
        ft.Icons.ADD_CARD,
    ),
    "/register/input": (
        "カード情報",
        Theme.SKY,
        Theme.SKY_SOFT,
        ft.Icons.BADGE,
    ),
    "/settings": (
        "設定",
        Theme.EQUIPMENT_GREEN,
        Theme.EQUIPMENT_GREEN_SOFT,
        ft.Icons.SETTINGS,
    ),
}


def tinted_shadow(color: str, alpha: int):
    return f"#{alpha:02X}{color.lstrip('#')}"


def card_shadow(accent: str = Theme.SKY, hovering=False):
    return ft.BoxShadow(
        blur_radius=22 if hovering else 17,
        spread_radius=0,
        color=tinted_shadow(
            accent,
            0x16 if hovering else 0x0D,
        ),
        offset=ft.Offset(
            0,
            6 if hovering else 4,
        ),
    )


def card(
    content,
    col=None,
    padding: int = 24,
    accent: str = Theme.SKY,
):
    panel = ft.Container(
        content=content,
        padding=padding,
        bgcolor=Theme.SURFACE,
        border=ft.border.all(
            1,
            tinted_shadow(accent, 0x28),
        ),
        border_radius=Theme.RADIUS,
        shadow=card_shadow(accent),
        col=col,
        scale=1.0,
        offset=ft.Offset(0, 0),
        animate_scale=ft.Animation(
            140,
            ft.AnimationCurve.EASE_OUT,
        ),
        animate_offset=ft.Animation(
            140,
            ft.AnimationCurve.EASE_OUT,
        ),
        animate=ft.Animation(
            140,
            ft.AnimationCurve.EASE_OUT,
        ),
    )

    def on_hover(e):
        hovering = e.data == "true"

        panel.scale = 1.005 if hovering else 1.0
        panel.offset = (
            ft.Offset(0, -0.008)
            if hovering
            else ft.Offset(0, 0)
        )
        panel.shadow = card_shadow(
            accent,
            hovering,
        )
        panel.border = ft.border.all(
            1,
            tinted_shadow(
                accent,
                0x42 if hovering else 0x28,
            ),
        )
        panel.update()

    panel.on_hover = on_hover
    return panel


def section_title(
    text: str,
    subtitle: str = None,
    accent: str = Theme.SKY,
):
    title_row = ft.Row(
        controls=[
            ft.Container(
                width=5,
                height=20,
                bgcolor=accent,
                border_radius=3,
            ),
            ft.Text(
                text,
                size=18,
                weight=ui_theme.FONT_WEIGHT,
                color=Theme.TEXT,
                font_family=ui_theme.FONT_FAMILY,
            ),
            ft.Container(
                expand=True,
                height=1,
                bgcolor=Theme.BORDER,
            ),
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    if not subtitle:
        return title_row

    return ft.Column(
        controls=[
            title_row,
            ft.Text(
                subtitle,
                size=12,
                color=Theme.TEXT_MUTED,
                font_family=ui_theme.FONT_FAMILY,
            ),
        ],
        spacing=6,
    )


def responsive_cards(cards_with_cols):
    return ft.ResponsiveRow(
        controls=[
            card(content, col=col)
            for content, col in cards_with_cols
        ],
        run_spacing=18,
        spacing=18,
    )


def primary_button(text: str, on_click, icon=None):
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        bgcolor=Theme.SKY,
        color="#FFFFFF",
        height=44,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(
                radius=Theme.RADIUS_SM,
            ),
            padding=ft.padding.symmetric(
                horizontal=20,
                vertical=12,
            ),
        ),
    )


def secondary_button(text: str, on_click, icon=None):
    return ft.OutlinedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        height=42,
        style=ft.ButtonStyle(
            color=Theme.TEXT,
            bgcolor=Theme.SURFACE,
            icon_color=Theme.TEXT_MUTED,
            overlay_color=Theme.SKY_SOFT,
            shape=ft.RoundedRectangleBorder(
                radius=Theme.RADIUS_SM,
            ),
            side=ft.BorderSide(
                1,
                Theme.BORDER,
            ),
            padding=ft.padding.symmetric(
                horizontal=16,
                vertical=11,
            ),
        ),
    )


def danger_button(text: str, on_click, icon=None):
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        height=42,
        bgcolor=ui_theme.DANGER_BG,
        color=Theme.DANGER,
        elevation=0,
        style=ft.ButtonStyle(
            icon_color=Theme.DANGER,
            overlay_color="#F8DDE2",
            shape=ft.RoundedRectangleBorder(
                radius=Theme.RADIUS_SM,
            ),
            padding=ft.padding.symmetric(
                horizontal=16,
                vertical=11,
            ),
        ),
    )


def back_button(
    page,
    route: str = "/index",
    on_click=None,
):
    handler = (
        on_click
        if on_click is not None
        else lambda e: page.go(route)
    )

    return ft.IconButton(
        icon=ft.Icons.ARROW_BACK,
        tooltip="戻る",
        width=ui_theme.NAV_BUTTON_SIZE,
        height=ui_theme.NAV_BUTTON_SIZE,
        icon_size=ui_theme.NAV_ICON_SIZE,
        icon_color=Theme.TEXT,
        bgcolor=Theme.SKY_SOFT,
        hover_color=Theme.SKY_SOFT,
        on_click=handler,
        style=ft.ButtonStyle(
            shape=ft.CircleBorder(),
            side=ft.BorderSide(1, "#FFFFFF"),
        ),
    )



def _page_title(title, accent, soft_color, icon):
    return ft.Column(
        width=1040,
        controls=[
            ft.Row(
                width=1040,
                controls=[
                    # タイトル左側のアイコン
                    ft.Container(
                        width=48,
                        height=48,
                        bgcolor=soft_color,
                        border_radius=24,
                        alignment=ft.alignment.center,
                        content=ft.Icon(
                            icon,
                            size=25,
                            color=accent,
                        ),
                    ),

                    # この文字の中心が画面中央になる
                    ft.Text(
                        title,
                        size=27,
                        color=Theme.TEXT,
                        weight=ui_theme.FONT_WEIGHT,
                        font_family=ui_theme.FONT_FAMILY,
                        text_align=ft.TextAlign.CENTER,
                        no_wrap=True,
                    ),

                    # アイコンと同じ幅を右側に確保する
                    ft.Container(
                        width=48,
                        height=48,
                    ),
                ],
                spacing=14,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),

            # 棒線は画面中央に固定
            ft.Row(
                width=1040,
                controls=[
                    ft.Container(
                        width=38,
                        height=2,
                        bgcolor=soft_color,
                        border_radius=1,
                    ),
                    ft.Icon(
                        ft.Icons.FAVORITE,
                        size=9,
                        color=Theme.PINK,
                    ),
                    ft.Container(
                        width=38,
                        height=2,
                        bgcolor=soft_color,
                        border_radius=1,
                    ),
                ],
                spacing=6,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        ],
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

def route_page_title(route):
    title, accent, soft_color, icon = _ROUTE_META.get(
        route,
        (
            "SmartKey",
            Theme.SKY,
            Theme.SKY_SOFT,
            ft.Icons.APPS,
        ),
    )

    return _page_title(
        title,
        accent,
        soft_color,
        icon,
    )


def _background_decorations():
    return [
        ft.Container(
            left=26,
            top=110,
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=42,
                        height=4,
                        bgcolor=Theme.PINK_SOFT,
                        border_radius=2,
                    ),
                    ft.Container(
                        width=27,
                        height=4,
                        bgcolor=Theme.SKY_SOFT,
                        border_radius=2,
                    ),
                    ft.Container(
                        width=15,
                        height=4,
                        bgcolor=Theme.LAVENDER_SOFT,
                        border_radius=2,
                    ),
                ],
                spacing=6,
            ),
        ),
        ft.Container(
            right=26,
            top=110,
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=15,
                        height=4,
                        bgcolor=Theme.LAVENDER_SOFT,
                        border_radius=2,
                    ),
                    ft.Container(
                        width=27,
                        height=4,
                        bgcolor=Theme.SKY_SOFT,
                        border_radius=2,
                    ),
                    ft.Container(
                        width=42,
                        height=4,
                        bgcolor=Theme.PINK_SOFT,
                        border_radius=2,
                    ),
                ],
                spacing=6,
            ),
        ),
    ]


_MANAGEMENT_TABS = (
    ("/user", "ユーザー管理", ft.Icons.PEOPLE, Theme.MAUVE, Theme.MAUVE_SOFT),
    ("/card", "カード管理", ft.Icons.CREDIT_CARD, Theme.MINT, Theme.MINT_SOFT),
    ("/face", "顔管理", ft.Icons.PERSON_SEARCH, Theme.LAVENDER, Theme.LAVENDER_SOFT),
)

MANAGEMENT_ROUTES = frozenset(
    item[0] for item in _MANAGEMENT_TABS
)


def management_tabs(page, active_route, on_change=None):
    try:
        counts = repo.get_management_registration_counts()
    except Exception:
        logger.exception("登録状況を取得できませんでした")
        counts = {}

    page.session.set("management_last_route", active_route)

    def count(key, unit):
        value = counts.get(key)
        return "-" if value is None else f"{value}{unit}"

    status_texts = {
        "/user": f"登録者数 {count('users', '人')}",
        "/card": (
            f"登録者 {count('card_users', '人')}  /  "
            f"登録枚数 {count('cards', '枚')}"
        ),
        "/face": (
            f"登録者 {count('face_users', '人')}  /  "
            f"登録顔数 {count('faces', '件')}"
        ),
    }

    def build_tab(item, is_last):
        route, label, icon, color, soft_color = item
        active = route == active_route

        def open_tab(_):
            if active:
                return

            if on_change is None:
                page.session.set(
                    "management_last_route",
                    route,
                )
                page.go(route)
                return

            on_change(route)

        tab = ft.Container(
            expand=True,
            height=72,
            bgcolor=soft_color if active else Theme.SURFACE,
            animate=ft.Animation(
                120,
                ft.AnimationCurve.EASE_OUT,
            ),
            ink=True,
            ink_color=soft_color,
            border=ft.border.only(
                bottom=ft.BorderSide(
                    3 if active else 1,
                    color if active else Theme.BORDER,
                )
            ),
            on_click=open_tab,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(
                                icon,
                                size=20,
                                color=(
                                    color
                                    if active
                                    else Theme.TEXT_MUTED
                                ),
                            ),
                            ft.Text(
                                label,
                                size=15,
                                weight=ft.FontWeight.W_700,
                                color=(
                                    Theme.TEXT
                                    if active
                                    else Theme.TEXT_MUTED
                                ),
                                font_family=ui_theme.FONT_FAMILY,
                            ),
                        ],
                        spacing=9,
                        alignment=ft.MainAxisAlignment.CENTER,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),

                    # ユーザー数・カード枚数・登録顔数を表示
                    ft.Text(
                        status_texts[route],
                        size=11,
                        color=(
                            color
                            if active
                            else Theme.TEXT_MUTED
                        ),
                        font_family=ui_theme.FONT_FAMILY,
                        text_align=ft.TextAlign.CENTER,
                        no_wrap=True,
                    ),
                ],
                spacing=3,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        def hover(e):
            if active:
                return

            tab.bgcolor = (
                soft_color
                if e.data == "true"
                else Theme.SURFACE
            )
            tab.update()

        tab.on_hover = hover
        return tab

    return ft.Container(
        width=1040,
        height=72,
        bgcolor=Theme.SURFACE,
        border=ft.border.all(1, Theme.BORDER),
        border_radius=8,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=ft.Row(
            controls=[
                build_tab(
                    item,
                    index == len(_MANAGEMENT_TABS) - 1,
                )
                for index, item
                in enumerate(_MANAGEMENT_TABS)
            ],
            spacing=0,
        ),
    )

def app_view(
    route: str,
    page,
    controls,
    back_route: str = "/index",
    on_back=None,
    page_title_control=None,
):
    title, accent, soft_color, icon = _ROUTE_META.get(
        route,
        (
            "SmartKey",
            Theme.SKY,
            Theme.SKY_SOFT,
            ft.Icons.APPS,
        ),
    )

    page.bgcolor = Theme.BG

    # 管理画面内ではヘッダーとタブを重複させず、本文だけ返す
    if (
        route in MANAGEMENT_ROUTES
        and getattr(page, "_management_embed_mode", False)
    ):
        return ft.Column(
            controls=list(controls[1:]),
            spacing=20,
        )

    header = ft.Row(
        controls=[
            ft.Text(
                "SmartKey",
                size=20,
                color=Theme.TEXT,
                weight=ui_theme.FONT_WEIGHT,
                font_family=ui_theme.FONT_FAMILY,
            ),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    if page_title_control is None:
        page_title_control = _page_title(
            title,
            accent,
            soft_color,
            icon,
        )

    page_controls = [
        header,
        page_title_control,
        *controls,
        ft.Container(height=90),
    ]

    content = ft.Container(
        width=1040,
        expand=True,
        content=ft.Column(
            controls=page_controls,
            spacing=20,
            scroll=ft.ScrollMode.HIDDEN,
            expand=True,
        ),
    )

    fixed_back_button = ft.Container(
        left=34,
        bottom=24,
        content=back_button(
            page,
            back_route,
            on_click=on_back,
        ),
    )

    return ft.View(
        route=route,
        padding=0,
        bgcolor=Theme.BG,
        controls=[
            ft.Stack(
                controls=[
                    *_background_decorations(),
                    ft.Container(
                        left=0,
                        right=0,
                        top=0,
                        bottom=0,
                        padding=ft.padding.only(
                            left=34,
                            top=26,
                            right=34,
                            bottom=16,
                        ),
                        alignment=ft.alignment.top_center,
                        content=content,
                    ),
                    fixed_back_button,
                ],
                expand=True,
            )
        ],
    )


def empty_state(
    message: str,
    icon=ft.Icons.INBOX_OUTLINED,
):
    return ft.Container(
        padding=ft.padding.symmetric(vertical=44),
        alignment=ft.alignment.center,
        content=ft.Column(
            controls=[
                ft.Container(
                    width=64,
                    height=64,
                    bgcolor=Theme.SKY_SOFT,
                    border_radius=32,
                    alignment=ft.alignment.center,
                    content=ft.Icon(
                        icon,
                        size=30,
                        color=Theme.SKY,
                    ),
                ),
                ft.Text(
                    message,
                    size=13,
                    color=Theme.TEXT_MUTED,
                    font_family=ui_theme.FONT_FAMILY,
                ),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def pager(prev_btn, page_label, next_btn):
    return ft.Row(
        controls=[
            prev_btn,
            ft.Container(
                padding=ft.padding.symmetric(
                    horizontal=14,
                    vertical=9,
                ),
                bgcolor=Theme.SKY_SOFT,
                border_radius=8,
                content=page_label,
            ),
            next_btn,
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=14,
    )


def nav_card(page, icon, label: str, route: str, col=None):
    panel = card(
        content=ft.Column(
            controls=[
                ft.Container(
                    width=60,
                    height=60,
                    bgcolor=Theme.SKY_SOFT,
                    border_radius=30,
                    alignment=ft.alignment.center,
                    content=ft.Icon(
                        icon,
                        size=30,
                        color=Theme.SKY,
                    ),
                ),
                ft.Text(
                    label,
                    size=16,
                    color=Theme.TEXT,
                    weight=ui_theme.FONT_WEIGHT,
                    font_family=ui_theme.FONT_FAMILY,
                ),
            ],
            spacing=12,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        col=col,
        padding=20,
    )
    panel.height = 145
    panel.alignment = ft.alignment.center
    panel.on_click = lambda _: page.go(route)
    return panel


# 汎用バッジ用のプリセット色(名前 -> (背景, 文字))
BADGE_BLUE = ("#E7F0FF", "#2F49AE")
BADGE_GREEN = ("#E6F7EE", "#1B7F4B")
BADGE_ORANGE = ("#FFF1E6", "#C2410C")
BADGE_GRAY = ("#EEF1F5", "#5A6675")


def badge(text: str, colors=BADGE_GRAY):
    """
    汎用の色付きバッジ。card_type_badgeを一般化したもの。
    入退室ログの「入室/退室」「カード/顔」などにも使える。

    Args:
        text (str): バッジに表示する文字
        colors: (背景色, 文字色) のタプル。BADGE_BLUE等のプリセットを渡す。

    Returns:
        ft.Container
    """
    bg, fg = colors
    return ft.Container(
        content=ft.Text(text, size=12, color=fg, weight=ft.FontWeight.W_500),
        bgcolor=bg,
        padding=ft.padding.symmetric(horizontal=10, vertical=4),
        border_radius=Theme.RADIUS_SM,
        alignment=ft.alignment.center,
    )


def show_confirm_dialog(page, message: str, on_confirm,
                        title: str = "確認", confirm_label: str = "はい",
                        cancel_label: str = "キャンセル"):
    """
    「〜しますか?」という確認ダイアログを出す共通部品。
    「はい」を押すと on_confirm が呼ばれ、その後ダイアログは閉じる。

    Args:
        page: ft.Page
        message (str): 確認メッセージ(例: "3件を削除しますか?")
        on_confirm: 「はい」押下時に呼ぶ関数(引数なし)
        title / confirm_label / cancel_label: 見出し・ボタン文言のカスタム用
    """
    dialog = ft.AlertDialog(modal=True)

    def confirm(e):
        page.close(dialog)
        on_confirm()

    dialog.title = ft.Text(title)
    dialog.content = ft.Text(message)
    dialog.actions = [
        ft.TextButton(cancel_label, autofocus=True, on_click=lambda e: page.close(dialog)),
        ft.TextButton(confirm_label, on_click=confirm),
    ]
    page.open(dialog)


def show_info_dialog(page, message: str, title: str = "完了", on_close=None):
    """
    完了・通知メッセージを出す共通部品(「閉じる」1つだけのダイアログ)。

    Args:
        page: ft.Page
        message (str): 表示メッセージ(例: "3件を削除しました。")
        title (str): 見出し
        on_close: 閉じた後に呼ぶ関数(省略時は閉じるだけ)
    """
    dialog = ft.AlertDialog(modal=True)

    def close(e):
        if on_close:
            on_close()
        else:
            page.close(dialog)

    dialog.title = ft.Text(title)
    dialog.content = ft.Text(message)
    dialog.actions = [
        ft.TextButton("閉じる", autofocus=True, on_click=close),
    ]
    page.open(dialog)


# カード種別ごとの色。プリセット定数を使うことで、他のバッジと色味が揃う。
_CARD_TYPE_COLORS = {
    "交通系ICカード": BADGE_BLUE,
    "クレジットカード": BADGE_GREEN,
    "その他": BADGE_GRAY,
}


def card_type_badge(card_type_value: str):
    """
    カード種別を、色付きの小さなバッジで表示する共通部品。
    「どの種別が何色か」はこの関数の中で解決するので、呼び出し側は
    値を渡すだけでよく、色を意識しなくてよい。

    見た目そのものは汎用の badge() に委譲しているため、バッジのデザインを
    変えたい時は badge() 側だけ直せば、ここにも自動的に反映される。

    Args:
        card_type_value (str): CardType.xxx.value の文字列(例: "交通系ICカード")

    Returns:
        ft.Container
    """
    colors = _CARD_TYPE_COLORS.get(card_type_value, BADGE_GRAY)
    return badge(card_type_value, colors)


def centered_cell(content, width: int):
    """
    DataTableのヘッダー/セルの中身を、指定した幅の中で中央寄せするヘルパー。
    ヘッダー(DataColumn)とデータ(DataCell)の両方で、同じ列には同じwidthを
    使うことで、中央線がきれいに揃う。

    Args:
        content: セルに入れる中身(Text, バッジ, Checkboxなど)
        width (int): その列の幅。ヘッダーとデータで必ず同じ値にすること。

    Returns:
        ft.Container
    """
    return ft.Container(
        content=content,
        alignment=ft.alignment.center,
        width=width,
    )


def show_error_dialog(page: ft.Page, message: str, go_home: bool = False):
    """
    予期しないエラー(DBエラー等)が起きた時、ユーザーに分かる形で伝える共通ダイアログ。
    詳細な原因はlogger側に出す想定で、ここでは利用者向けの平易なメッセージのみ表示する。

    Args:
        page (ft.Page): 表示先のページ
        message (str): ユーザーに見せるメッセージ(内部エラーの詳細は含めない)
        go_home (bool): Trueなら「閉じる」を押した後にホーム(/index)へ遷移する。
                        Falseならダイアログを閉じるだけで、その画面に留まる(デフォルト)。
    """
    def on_close(e):
        if go_home:
            go_home()
        else:
            page.close(dialog)

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("エラー"),
        content=ft.Text(message),
        actions=[
            ft.TextButton("閉じる", autofocus=True, on_click=on_close),
        ],
    )
    page.open(dialog)


def build_user_option(user) -> ft.AutoCompleteSuggestion:
    """
    User1件からAutoCompleteSuggestionを組み立てる。

    重要: Flet の AutoComplete は「key」に対してユーザー入力をマッチング
    (部分一致・大文字小文字無視)する。「value」は選択後に入力欄へ表示される
    だけで、絞り込み対象ではない。そのため:

    key:   検索対象にしたい文字列を全部入れる。漢字・カタカナ・ひらがな・ローマ字を
           連結し、さらに末尾に "#<user_id>" を付けて、選択時にuser_idを復元できるようにする。
           例: "山田太郎 ヤマダタロウ やまだたろう yamadatarou #1"
           (これで「やまだ」「ヤマダ」「yamada」「山田」いずれの入力でもヒットする)
    value: 入力欄に表示される名前。人が見て分かる表示用。
           例: "山田太郎(ヤマダタロウ)"
    """
    romaji = jt.katakana_to_romaji(user.user_kana)
    hiragana = jt.katakana_to_hiragana(user.user_kana)
    key = f"{user.user_name} {user.user_kana} {hiragana} {romaji} #{user.id}"
    value = f"{user.user_name}({user.user_kana})"
    return ft.AutoCompleteSuggestion(key=key, value=value)


def extract_user_id_from_key(key: str) -> int:
    """
    build_user_option が作った key の末尾 "#<user_id>" から user_id を取り出す。
    """
    return int(key.rsplit("#", 1)[1])


def build_user_autocomplete(users, on_selected, width: int = 300, height: int = 56):
    """
    ユーザー検索用のAutocompleteを組み立てて返す共通部品。
    各画面はこれを呼ぶだけで、同じ検索UIを使える(Thymeleafのフラグメント的な使い方)。

    絞り込みはFletのAutoComplete標準機能(keyに対する部分一致)に任せる。
    keyに漢字・カナ・ローマ字を含めてあるので、表記ゆれに対応できる。
    選択されたら、keyの末尾に埋め込んだuser_idを取り出してon_selectedに渡す。

    Args:
        users: 全ユーザー一覧(repo.get_all_users()の結果)
        on_selected: 選択時に呼ばれるコールバック。引数として user_id(int) を受け取る。

    Returns:
        ft.AutoComplete
    """
    def handle_select(e: ft.ControlEvent):
        on_selected(extract_user_id_from_key(e.selection.key))

    return ft.Container(
        width=width,
        height=height,
        content=ft.AutoComplete(
            suggestions=[build_user_option(u) for u in users],
            on_select=handle_select,
        )
    )