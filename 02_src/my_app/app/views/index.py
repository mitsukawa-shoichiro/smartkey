import logging
import asyncio
from dataclasses import dataclass

from datetime import datetime
import my_app.db.repository as repo
from my_app.models.ENUMS import EventType

import flet as ft
from my_app.ui import theme as ui_theme

logger = logging.getLogger(__name__)


# ===================================================
# 基本設定
# ===================================================

FONT_FAMILY = "Noto Sans JP"
FONT_WEIGHT = ft.FontWeight.W_900

BACKGROUND = "#FFFFFF"
CARD = "#FFFFFF"

TEXT = "#3A4C57"
TEXT_MUTED = "#79888E"

BORDER = "#DCE5E8"
BORDER_HOVER = "#C8D7DD"
SECTION_LINE = "#E8EDEF"

PINK = "#E36C98"
PINK_SOFT = "#FCE8F0"

SKY = "#529BC3"
SKY_SOFT = "#E5F2F8"

MINT = "#57A188"
MINT_SOFT = "#E6F3ED"

LAVENDER = "#8975B2"
LAVENDER_SOFT = "#EFEBF7"

MAUVE = "#A17C9F"
MAUVE_SOFT = "#F4EBF2"

LOG_BLUE = "#4F8FAF"
LOG_BLUE_SOFT = "#E4F1F7"

EQUIPMENT_GREEN = "#4F9475"
EQUIPMENT_GREEN_SOFT = "#E4F2EA"

GOLD = "#C7962E"
GOLD_SOFT = "#FFF5D9"

SILVER = "#829198"
SILVER_SOFT = "#EEF2F3"

BRONZE = "#B87850"
BRONZE_SOFT = "#F8ECE5"


@dataclass(frozen=True)
class MenuItem:
    label: str
    route: str
    icon: str
    color: str
    soft_color: str
    icon_size: int


MAIN_ITEMS = (
    MenuItem("管理", "/management", ft.Icons.GRID_VIEW,
            MINT, MINT_SOFT, 40),
    MenuItem("入退室ログ", "/access_logs", ft.Icons.SENSOR_DOOR,
            LOG_BLUE, LOG_BLUE_SOFT, 38),
    MenuItem("設定", "/settings", ft.Icons.SETTINGS,
            EQUIPMENT_GREEN, EQUIPMENT_GREEN_SOFT, 40),
)

MANAGEMENT_ITEMS = (
    MenuItem("カード管理", "/card", ft.Icons.CREDIT_CARD,
            MINT, MINT_SOFT, 38),
    MenuItem("顔管理", "/face", ft.Icons.PERSON_SEARCH,
            LAVENDER, LAVENDER_SOFT, 40),
    MenuItem("ユーザー管理", "/user", ft.Icons.PEOPLE,
            MAUVE, MAUVE_SOFT, 37),
)


# ===================================================
# 共通部品
# ===================================================

def tinted_shadow(
    color: str,
    alpha: int,
):
    return f"#{alpha:02X}{color.lstrip('#')}"


def header_action(
    icon: str,
    tooltip: str,
    color: str,
    soft_color: str,
    on_click,
):
    action = ft.Container(
        scale=1.0,
        offset=ft.Offset(0, 0),
        animate_scale=ft.Animation(
            140,
            ft.AnimationCurve.EASE_OUT,
        ),
        animate_offset=ft.Animation(
            130,
            ft.AnimationCurve.EASE_OUT,
        ),
        content=ft.IconButton(
            icon=icon,
            tooltip=tooltip,
            width=ui_theme.NAV_BUTTON_SIZE,
            height=ui_theme.NAV_BUTTON_SIZE,
            icon_size=ui_theme.NAV_ICON_SIZE,
            icon_color=color,
            bgcolor=soft_color,
            hover_color=soft_color,
            on_click=on_click,
            style=ft.ButtonStyle(
                shape=ft.CircleBorder(),
                side=ft.BorderSide(1, "#FFFFFF"),
            ),
        ),
    )

    def on_hover(e):
        hovering = e.data == "true"

        action.scale = 1.06 if hovering else 1.0
        action.offset = (
            ft.Offset(0, -0.05)
            if hovering
            else ft.Offset(0, 0)
        )
        action.update()

    action.on_hover = on_hover
    return action


def entry_ranking_action(page: ft.Page):
    ranking_list = ft.Column(
        spacing=8,
        expand=True,
        scroll=ft.ScrollMode.HIDDEN,
    )

    def ranking_row(item):
        rank = item["rank"]

        if rank == 1:
            color, soft_color = GOLD, GOLD_SOFT
            rank_control = ft.Text(
                "♛",
                size=23,
                color=color,
                font_family="Segoe UI Symbol",
            )
        elif rank == 2:
            color, soft_color = SILVER, SILVER_SOFT
            rank_control = ft.Text("2", size=17, color=color)
        elif rank == 3:
            color, soft_color = BRONZE, BRONZE_SOFT
            rank_control = ft.Text("3", size=17, color=color)
        else:
            color, soft_color = TEXT_MUTED, "#F8FBFC"
            rank_control = ft.Text(str(rank), size=15, color=color)

        last_entry = item["last_entry"]
        time_text = (
            last_entry.strftime("%H:%M")
            if last_entry is not None
            else "時刻不明"
        )

        return ft.Container(
            bgcolor=soft_color,
            border=ft.border.all(1, color),
            border_radius=8,
            content=ft.ListTile(
                leading=ft.Container(
                    width=40,
                    height=40,
                    border_radius=20,
                    bgcolor=CARD,
                    alignment=ft.alignment.center,
                    content=rank_control,
                ),
                title=ft.Text(
                    item["user_name"],
                    size=14,
                    color=TEXT,
                    weight=FONT_WEIGHT,
                    font_family=FONT_FAMILY,
                    no_wrap=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                subtitle=ft.Text(
                    f"最終入室 {time_text}",
                    size=11,
                    color=TEXT_MUTED,
                ),
                trailing=ft.Text(
                    f"{item['entry_count']} 回",
                    size=16,
                    color=color,
                    weight=FONT_WEIGHT,
                    font_family=FONT_FAMILY,
                ),
            ),
        )

    ranking_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Text(
                    "♛",
                    size=25,
                    color=GOLD,
                    font_family="Segoe UI Symbol",
                ),
                ft.Text(
                    "本日の入室ランキング",
                    size=19,
                    color=TEXT,
                    weight=FONT_WEIGHT,
                    font_family=FONT_FAMILY,
                ),
            ],
            spacing=10,
        ),
        content=ft.Container(
            width=480,
            height=390,
            content=ranking_list,
        ),
        actions=[
            ft.TextButton(
                "閉じる",
                on_click=lambda _: page.close(ranking_dialog),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=CARD,
        shape=ft.RoundedRectangleBorder(radius=8),
    )

    async def open_ranking(_):
        ranking_list.controls = [
            ft.Container(
                height=330,
                alignment=ft.alignment.center,
                content=ft.ProgressRing(
                    width=28,
                    height=28,
                    color=GOLD,
                ),
            )
        ]
        page.open(ranking_dialog)

        try:
            ranking = await asyncio.to_thread(
                repo.get_today_entry_ranking,
                10,
            )

            if page.route != "/index":
                return

            if ranking:
                ranking_list.controls = [
                    ranking_row(item)
                    for item in ranking
                ]
            else:
                ranking_list.controls = [
                    ft.Container(
                        height=330,
                        alignment=ft.alignment.center,
                        content=ft.Column(
                            controls=[
                                ft.Icon(
                                    ft.Icons.EMOJI_EVENTS_OUTLINED,
                                    size=40,
                                    color=GOLD,
                                ),
                                ft.Text(
                                    "本日の入室記録はありません",
                                    color=TEXT_MUTED,
                                    font_family=FONT_FAMILY,
                                ),
                            ],
                            spacing=12,
                            horizontal_alignment=(
                                ft.CrossAxisAlignment.CENTER
                            ),
                        ),
                    )
                ]

            ranking_list.update()

        except Exception:
            logger.exception(
                "本日の入室ランキングを表示できませんでした"
            )
            ranking_list.controls = [
                ft.Container(
                    height=330,
                    alignment=ft.alignment.center,
                    content=ft.Text(
                        "ランキングを取得できませんでした",
                        color=PINK,
                        font_family=FONT_FAMILY,
                    ),
                )
            ]
            ranking_list.update()

    action = ft.Container(
        scale=1.0,
        offset=ft.Offset(0, 0),
        animate_scale=ft.Animation(
            140,
            ft.AnimationCurve.EASE_OUT,
        ),
        animate_offset=ft.Animation(
            130,
            ft.AnimationCurve.EASE_OUT,
        ),
        content=ft.TextButton(
            content=ft.Text(
                "♛",
                size=25,
                color=GOLD,
                font_family="Segoe UI Symbol",
            ),
            tooltip="本日の入室ランキング",
            width=ui_theme.NAV_BUTTON_SIZE,
            height=ui_theme.NAV_BUTTON_SIZE,
            on_click=open_ranking,
            style=ft.ButtonStyle(
                bgcolor=GOLD_SOFT,
                overlay_color="#22C7962E",
                shape=ft.CircleBorder(),
                side=ft.BorderSide(1, "#FFFFFF"),
                padding=0,
            ),
        ),
    )

    def on_hover(e):
        hovering = e.data == "true"
        action.scale = 1.06 if hovering else 1.0
        action.offset = (
            ft.Offset(0, -0.05)
            if hovering
            else ft.Offset(0, 0)
        )
        action.update()

    action.on_hover = on_hover
    return action

def floating_header(page: ft.Page):
    def logout(_):
        logger.info("ログアウトしました")
        page.go("/")

    return ft.Row(
        controls=[
            ft.Container(
                height=ui_theme.NAV_BUTTON_SIZE,
                expand=True,
                alignment=ft.alignment.top_left,
                content=ft.Text(
                    "SmartKey",
                    size=20,
                    color=TEXT,
                    weight=FONT_WEIGHT,
                    font_family=FONT_FAMILY,
                ),
            ),

            # ログアウトの左側
            entry_ranking_action(page),

            header_action(
                icon=ft.Icons.LOGOUT,
                tooltip="ログアウト",
                color=PINK,
                soft_color=PINK_SOFT,
                on_click=logout,
            ),
        ],
        spacing=10,
        vertical_alignment=(
            ft.CrossAxisAlignment.START
        ),
    )


def section_title(
    title: str,
    color: str,
    icon: str,
):
    return ft.Row(
        controls=[
            ft.Container(
                width=5,
                height=20,
                bgcolor=color,
                border_radius=3,
            ),
            ft.Icon(
                icon,
                size=16,
                color=color,
            ),
            ft.Text(
                title,
                size=16,
                color=TEXT,
                weight=FONT_WEIGHT,
                font_family=FONT_FAMILY,
            ),
            ft.Container(
                expand=True,
                height=1,
                bgcolor=SECTION_LINE,
            ),
        ],
        spacing=9,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def icon_panel(
    item: MenuItem,
    size: int,
):
    return ft.Container(
        width=size,
        height=size,
        bgcolor=item.soft_color,
        border=ft.border.all(
            2,
            "#FFFFFF",
        ),
        border_radius=size // 2,
        alignment=ft.alignment.center,
        scale=1.0,
        animate_scale=ft.Animation(
            150,
            ft.AnimationCurve.EASE_OUT,
        ),
        shadow=ft.BoxShadow(
            blur_radius=12,
            color=tinted_shadow(
                item.color,
                0x10,
            ),
            offset=ft.Offset(0, 3),
        ),
        content=ft.Icon(
            item.icon,
            size=item.icon_size,
            color=item.color,
        ),
    )


def arrow_control(
    item: MenuItem,
    size: int,
    icon_size: int,
):
    return ft.Container(
        width=size,
        height=size,
        bgcolor="#FFFFFF",
        border=ft.border.all(
            1,
            BORDER,
        ),
        border_radius=size // 2,
        alignment=ft.alignment.center,
        scale=1.0,
        animate=ft.Animation(
            130,
            ft.AnimationCurve.EASE_OUT,
        ),
        animate_scale=ft.Animation(
            150,
            ft.AnimationCurve.EASE_OUT,
        ),
        content=ft.Icon(
            ft.Icons.CHEVRON_RIGHT,
            size=icon_size,
            color=TEXT_MUTED,
        ),
    )


def centered_hover_signal(item: MenuItem):
    line = ft.Container(
        width=0,
        height=3,
        bgcolor=item.color,
        border_radius=2,
        animate=ft.Animation(
            140,
            ft.AnimationCurve.EASE_OUT,
        ),
    )

    host = ft.Container(
        left=0,
        right=0,
        top=0,
        height=3,
        alignment=ft.alignment.top_center,
        content=line,
    )

    return host, line


def update_arrow_hover(
    arrow: ft.Container,
    item: MenuItem,
    hovering: bool,
):
    arrow.bgcolor = (
        item.color
        if hovering
        else "#FFFFFF"
    )

    arrow.border = ft.border.all(
        1,
        item.color
        if hovering
        else BORDER,
    )

    arrow.content.color = (
        "#FFFFFF"
        if hovering
        else TEXT_MUTED
    )

    arrow.scale = 1.08 if hovering else 1.0


# ===================================================
# 新規登録カード
# ===================================================

def register_card(
    page: ft.Page,
    item: MenuItem,
):
    icon_box = icon_panel(
        item,
        size=86,
    )

    arrow = arrow_control(
        item=item,
        size=40,
        icon_size=25,
    )

    signal_host, signal_line = (
        centered_hover_signal(item)
    )

    card = ft.Container(
        width=370,
        height=148,
        bgcolor=CARD,
        border=ft.border.all(
            1,
            item.soft_color,
        ),
        border_radius=8,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        scale=1.0,
        offset=ft.Offset(0, 0),
        shadow=ft.BoxShadow(
            blur_radius=22,
            spread_radius=1,
            color=tinted_shadow(
                item.color,
                0x11,
            ),
            offset=ft.Offset(0, 5),
        ),
        animate=ft.Animation(
            150,
            ft.AnimationCurve.EASE_OUT,
        ),
        animate_scale=ft.Animation(
            150,
            ft.AnimationCurve.EASE_OUT,
        ),
        animate_offset=ft.Animation(
            140,
            ft.AnimationCurve.EASE_OUT,
        ),
        on_click=lambda _: page.go(item.route),
        content=ft.Stack(
            controls=[
                ft.Container(
                    left=0,
                    right=0,
                    top=0,
                    bottom=0,
                    padding=ft.padding.symmetric(
                        horizontal=26,
                        vertical=22,
                    ),
                    content=ft.Row(
                        controls=[
                            icon_box,
                            ft.Text(
                                item.label,
                                size=21,
                                color=TEXT,
                                weight=FONT_WEIGHT,
                                font_family=FONT_FAMILY,
                                no_wrap=True,
                            ),
                            ft.Container(expand=True),
                            arrow,
                        ],
                        spacing=22,
                        vertical_alignment=(
                            ft.CrossAxisAlignment.CENTER
                        ),
                    ),
                ),
                signal_host,
            ],
        ),
    )

    def on_hover(e):
        hovering = e.data == "true"

        card.scale = 1.01 if hovering else 1.0
        card.offset = (
            ft.Offset(0, -0.025)
            if hovering
            else ft.Offset(0, 0)
        )

        card.border = ft.border.all(
            1,
            BORDER_HOVER
            if hovering
            else item.soft_color,
        )

        card.shadow = ft.BoxShadow(
            blur_radius=27 if hovering else 22,
            spread_radius=1,
            color=tinted_shadow(
                item.color,
                0x18 if hovering else 0x11,
            ),
            offset=ft.Offset(
                0,
                7 if hovering else 5,
            ),
        )

        icon_box.scale = 1.04 if hovering else 1.0
        signal_line.width = 42 if hovering else 0

        update_arrow_hover(
            arrow,
            item,
            hovering,
        )

        card.update()

    card.on_hover = on_hover
    return card


# ===================================================
# 管理カード
# ===================================================

def management_card(
    page: ft.Page,
    item: MenuItem,
    width: int = 162,
    height: int = 176,
):
    icon_box = icon_panel(
        item,
        size=64,
    )

    arrow = arrow_control(
        item=item,
        size=27,
        icon_size=18,
    )

    signal_host, signal_line = (
        centered_hover_signal(item)
    )

    card = ft.Container(
        width=width,
        height=height,
        bgcolor=CARD,
        border=ft.border.all(
            1,
            item.soft_color,
        ),
        border_radius=8,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        scale=1.0,
        offset=ft.Offset(0, 0),
        shadow=ft.BoxShadow(
            blur_radius=18,
            color=tinted_shadow(
                item.color,
                0x0F,
            ),
            offset=ft.Offset(0, 4),
        ),
        animate=ft.Animation(
            140,
            ft.AnimationCurve.EASE_OUT,
        ),
        animate_scale=ft.Animation(
            140,
            ft.AnimationCurve.EASE_OUT,
        ),
        animate_offset=ft.Animation(
            130,
            ft.AnimationCurve.EASE_OUT,
        ),
        on_click=lambda _: page.go(item.route),
        content=ft.Stack(
            controls=[
                ft.Container(
                    left=0,
                    right=0,
                    top=0,
                    bottom=0,
                    padding=ft.padding.symmetric(
                        horizontal=14,
                        vertical=18,
                    ),
                    content=ft.Column(
                        controls=[
                            icon_box,
                            ft.Text(
                                item.label,
                                size=15,
                                color=TEXT,
                                weight=FONT_WEIGHT,
                                font_family=FONT_FAMILY,
                                text_align=ft.TextAlign.CENTER,
                                no_wrap=True,
                            ),
                            arrow,
                        ],
                        spacing=12,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=(
                            ft.CrossAxisAlignment.CENTER
                        ),
                    ),
                ),
                signal_host,
            ],
        ),
    )

    def on_hover(e):
        hovering = e.data == "true"

        card.scale = 1.018 if hovering else 1.0
        card.offset = (
            ft.Offset(0, -0.025)
            if hovering
            else ft.Offset(0, 0)
        )

        card.border = ft.border.all(
            1,
            BORDER_HOVER
            if hovering
            else item.soft_color,
        )

        card.shadow = ft.BoxShadow(
            blur_radius=23 if hovering else 18,
            color=tinted_shadow(
                item.color,
                0x16 if hovering else 0x0F,
            ),
            offset=ft.Offset(
                0,
                6 if hovering else 4,
            ),
        )

        icon_box.scale = 1.045 if hovering else 1.0
        signal_line.width = 30 if hovering else 0

        update_arrow_hover(
            arrow,
            item,
            hovering,
        )

        card.update()

    card.on_hover = on_hover
    return card


# ===================================================
# 背景装飾
# ===================================================

def pastel_ribbon(
    colors: list[str],
    reverse: bool = False,
):
    widths = [42, 28, 16]

    if reverse:
        widths = list(reversed(widths))
        colors = list(reversed(colors))

    return ft.Row(
        controls=[
            ft.Container(
                width=width,
                height=4,
                bgcolor=color,
                border_radius=2,
            )
            for width, color in zip(
                widths,
                colors,
            )
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def background_decorations():
    return [
        ft.Container(
            left=28,
            top=105,
            content=ft.Column(
                controls=[
                    pastel_ribbon(
                        [
                            PINK_SOFT,
                            SKY_SOFT,
                            LAVENDER_SOFT,
                        ]
                    ),
                    ft.Container(
                        padding=ft.padding.only(left=8),
                        content=ft.Icon(
                            ft.Icons.FAVORITE_BORDER,
                            size=13,
                            color=PINK,
                            opacity=0.35,
                        ),
                    ),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            ),
        ),
        ft.Container(
            right=28,
            top=105,
            content=ft.Column(
                controls=[
                    pastel_ribbon(
                        [
                            PINK_SOFT,
                            SKY_SOFT,
                            LAVENDER_SOFT,
                        ],
                        reverse=True,
                    ),
                    ft.Container(
                        padding=ft.padding.only(right=8),
                        alignment=ft.alignment.center_right,
                        content=ft.Icon(
                            ft.Icons.FAVORITE_BORDER,
                            size=13,
                            color=PINK,
                            opacity=0.35,
                        ),
                    ),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.END,
            ),
        ),
        ft.Container(
            left=28,
            bottom=38,
            content=ft.Column(
                controls=[
                    ft.Container(
                        padding=ft.padding.only(left=8),
                        content=ft.Icon(
                            ft.Icons.FAVORITE_BORDER,
                            size=13,
                            color=MINT,
                            opacity=0.32,
                        ),
                    ),
                    pastel_ribbon(
                        [
                            MINT_SOFT,
                            LAVENDER_SOFT,
                            SKY_SOFT,
                        ]
                    ),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            ),
        ),
        ft.Container(
            right=28,
            bottom=38,
            content=ft.Column(
                controls=[
                    ft.Container(
                        padding=ft.padding.only(right=8),
                        alignment=ft.alignment.center_right,
                        content=ft.Icon(
                            ft.Icons.FAVORITE_BORDER,
                            size=13,
                            color=MINT,
                            opacity=0.32,
                        ),
                    ),
                    pastel_ribbon(
                        [
                            MINT_SOFT,
                            LAVENDER_SOFT,
                            SKY_SOFT,
                        ],
                        reverse=True,
                    ),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.END,
            ),
        ),
        ft.Container(
            left=17,
            top=245,
            content=ft.Column(
                controls=[
                    ft.Container(
                        width=4,
                        height=35,
                        bgcolor=PINK_SOFT,
                        border_radius=2,
                    ),
                    ft.Container(
                        width=4,
                        height=19,
                        bgcolor=SKY_SOFT,
                        border_radius=2,
                    ),
                ],
                spacing=6,
            ),
        ),
        ft.Container(
            right=17,
            top=245,
            content=ft.Column(
                controls=[
                    ft.Container(
                        width=4,
                        height=35,
                        bgcolor=PINK_SOFT,
                        border_radius=2,
                    ),
                    ft.Container(
                        width=4,
                        height=19,
                        bgcolor=SKY_SOFT,
                        border_radius=2,
                    ),
                ],
                spacing=6,
            ),
        ),
    ]


# ===================================================
# メイン画面
# ===================================================

def index_view(page: ft.Page):
    def format_access_summary(summary):
        entry_count = summary.get("entry_count")
        exit_count = summary.get("exit_count")
        latest = summary.get("latest")

        entry_text = (
            "-" if entry_count is None
            else f"{entry_count}件"
        )
        exit_text = (
            "-" if exit_count is None
            else f"{exit_count}件"
        )

        if latest is None:
            latest_text = "入退室記録はありません"
        else:
            event_text = (
                "入室"
                if latest["event_type"] == EventType.ENTRY
                else "退室"
            )
            timestamp = latest["timestamp"]

            if timestamp is None:
                time_text = "時刻不明"
            elif timestamp.date() == datetime.now().date():
                time_text = timestamp.strftime("%H:%M")
            else:
                time_text = timestamp.strftime("%m/%d %H:%M")

            latest_text = (
                f"{latest['user_name']} ・ "
                f"{event_text} ・ {time_text}"
            )

        return entry_text, exit_text, latest_text


    try:
        access_summary = (
            repo.get_main_menu_access_summary()
        )
    except Exception:
        logger.exception(
            "本日の利用状況を取得できませんでした"
        )
        access_summary = {
            "entry_count": None,
            "exit_count": None,
            "latest": None,
        }

    entry_text, exit_text, latest_text = (
        format_access_summary(access_summary)
    )

    page.title = "入退室管理システム"
    page.bgcolor = BACKGROUND

    title_area = ft.Column(
        controls=[
            ft.Text(
                "メインメニュー",
                size=29,
                color=TEXT,
                weight=FONT_WEIGHT,
                font_family=FONT_FAMILY,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Row(
                controls=[
                    ft.Container(
                        width=44,
                        height=2,
                        bgcolor=SKY_SOFT,
                        border_radius=1,
                    ),
                    ft.Icon(
                        ft.Icons.FAVORITE,
                        size=10,
                        color=PINK,
                    ),
                    ft.Container(
                        width=44,
                        height=2,
                        bgcolor=SKY_SOFT,
                        border_radius=1,
                    ),
                ],
                spacing=7,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        ],
        spacing=7,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    menu_cards = []

    for item in MAIN_ITEMS:
        menu_card = management_card(
            page,
            item,
            width=None,
            height=176,
        )
        menu_card.col = {
            "xs": 12,
            "sm": 4,
        }
        menu_cards.append(menu_card)

    menu_grid = ft.ResponsiveRow(
        controls=menu_cards,
        columns=12,
        spacing=24,
        run_spacing=18,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    entry_value_ref = ft.Ref[ft.Text]()
    exit_value_ref = ft.Ref[ft.Text]()
    latest_value_ref = ft.Ref[ft.Text]()

    def summary_item(
        icon,
        label,
        value,
        color,
        soft_color,
        col,
        value_size=21,
        value_ref=None,
    ):
        return ft.Container(
            col=col,
            padding=ft.padding.symmetric(
                horizontal=8,
                vertical=4,
            ),
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=36,
                        height=36,
                        bgcolor=soft_color,
                        border_radius=18,
                        alignment=ft.alignment.center,
                        content=ft.Icon(
                            icon,
                            size=19,
                            color=color,
                        ),
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(
                                label,
                                size=10,
                                color=TEXT_MUTED,
                                font_family=FONT_FAMILY,
                                no_wrap=True,
                            ),
                            ft.Text(
                                value,
                                ref=value_ref,
                                size=value_size,
                                color=color,
                                weight=FONT_WEIGHT,
                                font_family=FONT_FAMILY,
                                no_wrap=True,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                        spacing=0,
                        tight=True,
                        expand=True,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )


    summary_values = ft.Container(
        padding=ft.padding.symmetric(
            horizontal=12,
            vertical=10,
        ),
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        content=ft.ResponsiveRow(
            controls=[
                summary_item(
                    ft.Icons.LOGIN,
                    "本日の入室",
                    entry_text,
                    SKY,
                    SKY_SOFT,
                    col={
                        "xs": 12,
                        "md": 3,
                    },
                    value_ref=entry_value_ref,
                ),
                summary_item(
                    ft.Icons.LOGOUT,
                    "本日の退室",
                    exit_text,
                    PINK,
                    PINK_SOFT,
                    col={
                        "xs": 12,
                        "md": 3,
                    },
                    value_ref=exit_value_ref,
                ),
                summary_item(
                    ft.Icons.SCHEDULE,
                    "直近の入退室",
                    latest_text,
                    LOG_BLUE,
                    LOG_BLUE_SOFT,
                    col={
                        "xs": 12,
                        "md": 6,
                    },
                    value_size=14,
                    value_ref=latest_value_ref,
                ),
            ],
            columns=12,
            spacing=12,
            run_spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    today_summary = ft.Container(
        width=1040,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.TODAY,
                            size=17,
                            color=LOG_BLUE,
                        ),
                        ft.Text(
                            "本日の利用状況",
                            size=13,
                            weight=ft.FontWeight.W_700,
                            color=TEXT,
                        ),
                        ft.Container(
                            expand=True,
                            height=1,
                            bgcolor=BORDER,
                        ),
                    ],
                    spacing=9,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                summary_values,
            ],
            spacing=10,
        ),
    )

    menu_and_summary = ft.Container(
        expand=True,
        alignment=ft.alignment.center,
        content=ft.Column(
            controls=[
                ft.Container(
                    content=menu_grid,
                    offset=ft.Offset(
                        0,
                        -0.35,
                    ),
                ),
                today_summary,
            ],
            spacing=34,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    main_menu_section = ft.Container(
        expand=True,
        padding=ft.padding.symmetric(vertical=16),
        content=ft.Column(
            controls=[
                title_area,
                menu_and_summary,
            ],
            spacing=12,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    main_content = ft.Container(
        width=1040,
        expand=True,
        content=ft.Column(
            controls=[
                floating_header(page),
                main_menu_section,
            ],
            spacing=12,
            expand=True,
        ),
    )

    page_content = ft.Container(
        left=0,
        right=0,
        top=0,
        bottom=0,
        alignment=ft.alignment.top_center,
        padding=ft.padding.only(
            left=34,
            top=26,
            right=34,
            bottom=16,
        ),
        content=main_content,
    )

    background = ft.Container(
        expand=True,
        bgcolor=BACKGROUND,
        content=ft.Stack(
            controls=[
                *background_decorations(),
                page_content,
            ],
        ),
    )

    refresh_generation = (
        getattr(
            page,
            "_index_summary_generation",
            0,
        )
        + 1
    )
    page._index_summary_generation = (
        refresh_generation
    )


    async def refresh_today_summary():
        error_logged = False

        while True:
            await asyncio.sleep(1)


            if (
                getattr(page, "_app_closing", False)
                or page.route != "/index"
                or page._index_summary_generation != refresh_generation
            ):
                return

            try:
                summary = await asyncio.to_thread(
                    repo.get_main_menu_access_summary
                )
                values = format_access_summary(summary)

                controls = (
                    entry_value_ref.current,
                    exit_value_ref.current,
                    latest_value_ref.current,
                )

                if any(control is None for control in controls):
                    continue

                if tuple(
                    control.value for control in controls
                ) == values:
                    error_logged = False
                    continue

                if page.route != "/index":
                    return

                for control, value in zip(
                    controls,
                    values,
                ):
                    control.value = value

                today_summary.update()
                error_logged = False

            except Exception:
                if not error_logged:
                    logger.exception(
                        "本日の利用状況の更新に失敗しました"
                    )
                    error_logged = True


    previous_task = getattr(page, "_index_summary_task", None)
    if previous_task is not None and not previous_task.done():
        previous_task.cancel()

    page._index_summary_task = page.run_task(
        refresh_today_summary
    )

    return ft.View(
        route="/index",
        padding=0,
        bgcolor=BACKGROUND,
        controls=[background],
    )