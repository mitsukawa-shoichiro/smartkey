"""
ホーム画面(GUI)

左に機能の一覧を縦に並べ、クリックすると右側の大きな枠へ拡大移動する。
拡大中のカードをもう一度クリックすると、その画面へ遷移する。

Stackで絶対座標を指定し、Containerのanimate_position / animate_size で
位置とサイズの変化をアニメーションさせている。
"""
import logging
from dataclasses import dataclass

import flet as ft

from my_app.app.views.common import Theme, section_title

logger = logging.getLogger(__name__)

# ==========================================
# レイアウトサイズの定数
# ウィンドウは 1024x768 固定(main.pyw で min_width/min_height を指定)前提。
# 項目を増減させたら STAGE_HEIGHT の係数も直すこと。
# ==========================================
SMALL_WIDTH = 190
SMALL_HEIGHT = 64
SMALL_LEFT = 0           # 左列のx位置
SMALL_TOP_START = 0      # 一番上のアイテムのy位置
SMALL_GAP = 10           # アイテム同士の縦の間隔

BIG_LEFT = 215           # 右の大きな枠のx位置
BIG_TOP = 0
BIG_WIDTH = 670
BIG_HEIGHT = 508         # 左列全体の高さと揃える

SMALL_RADIUS = Theme.RADIUS_SM
BIG_RADIUS = Theme.RADIUS

STAGE_WIDTH = BIG_LEFT + BIG_WIDTH                       # 885
STAGE_HEIGHT = 7 * SMALL_HEIGHT + 6 * SMALL_GAP          # 508

# UNSELECTED_OPACITY = 0.4   # 他が選択されている間の、非選択カードの薄さ


# ==========================================
# グラデーションのプリセット (明るい側, 暗い側)
# 機能の系統ごとに色相を揃えている:
#   青  = 登録する系
#   紫  = 管理する系
#   緑  = 見る系
#   灰青 = 設定系
# ==========================================
GRAD_BLUE = ("#4C6EF5", "#3B5BDB")
GRAD_INDIGO = ("#5C7CFA", "#4263EB")
GRAD_VIOLET = ("#845EF7", "#7048E8")
GRAD_GRAPE = ("#9775FA", "#7950F2")
GRAD_PLUM = ("#B197FC", "#845EF7")
GRAD_TEAL = ("#20C997", "#0CA678")
GRAD_SLATE = ("#748FFC", "#5C7CFA")


@dataclass(frozen=True)
class NavItem:
    """
    ホーム画面のナビゲーション項目1件。

    要素が5つに増えて item[2] が何なのか読めなくなったため、タプルから
    データクラスに変更した(属性が増えたら見直す、という判断の結果)。
    frozen=True で書き換え不可にしている(定義であって状態ではないため)。
    """
    icon: str
    label: str
    route: str
    description: str
    gradient: tuple   # (明るい側の色, 暗い側の色)


# ナビゲーション項目。機能を増やす時はここに1行足す。
# 増やしたら STAGE_HEIGHT の係数(7)も直すこと。
_NAV_ITEMS = [
    NavItem(ft.Icons.ADD_CARD, "カード登録", "/register",
            "新しいICカードを読み取って、利用者に紐づけて登録します", GRAD_BLUE),
    NavItem(ft.Icons.FACE, "顔登録", "/face_register",
            "カメラで顔を撮影して、利用者の顔情報を登録します", GRAD_INDIGO),
    NavItem(ft.Icons.CREDIT_CARD, "カード管理", "/card",
            "登録済みのカードを一覧で確認し、不要なものを削除します", GRAD_VIOLET),
    NavItem(ft.Icons.PERSON_SEARCH, "顔認証管理", "/face",
            "登録済みの顔情報を一覧で確認し、不要なものを削除します", GRAD_GRAPE),
    NavItem(ft.Icons.PEOPLE, "ユーザー管理", "/user",
            "利用者の氏名・カナ氏名を確認・編集・削除します", GRAD_PLUM),
    NavItem(ft.Icons.SENSOR_DOOR, "入退室ログ", "/access_logs",
            "いつ誰がどの方法で入退室したかの履歴を検索します", GRAD_TEAL),
    NavItem(ft.Icons.SETTINGS, "設備登録", "/camera_register",
            "カメラやカードリーダーなどの機器を設定します", GRAD_SLATE),
]


def _make_gradient(colors) -> ft.LinearGradient:
    """左上から右下へ流れる斜めのグラデーションを作る"""
    return ft.LinearGradient(
        begin=ft.alignment.top_left,
        end=ft.alignment.bottom_right,
        colors=list(colors),
    )


def _make_glow(color: str) -> ft.BoxShadow:
    """
    拡大中のカードの下に敷く、その色みを帯びた影。
    8桁16進の先頭2桁が不透明度(59 = 約35%)。
    """
    return ft.BoxShadow(
        spread_radius=0,
        blur_radius=28,
        color="#59" + color.lstrip("#"),
        offset=ft.Offset(0, 10),
    )


def index_view(page: ft.Page):
    page.title = "ドア開閉システム"
    page.bgcolor = Theme.BG

    # 選択中のカードのindex(未選択ならNone)。
    # dictにしておくと、入れ子の関数から nonlocal 無しで書き換えられる。
    state = {"selected_index": None}

    containers = []
    icons = []          # 拡大時にサイズ・色を変えるので、個別に参照を持っておく
    labels = []
    descriptions = []

    def small_top_for(index: int) -> int:
        """未選択時、左列に縦に並べた時のy位置"""
        return SMALL_TOP_START + index * (SMALL_HEIGHT + SMALL_GAP)

    def update_all_positions():
        """
        selected_index に合わせて、全カードの位置・サイズ・色を更新する。
        Containerに animate_* を設定してあるので、値を変えるだけで
        アニメーションしながら移動する。
        """
        selected = state["selected_index"]

        for i, c in enumerate(containers):
            item = _NAV_ITEMS[i]

            if selected == i:
                # 選択中 → 右の大きな枠へ。ここで初めてグラデーションが現れる。
                c.left = BIG_LEFT
                c.top = BIG_TOP
                c.width = BIG_WIDTH
                c.height = BIG_HEIGHT
                c.border_radius = BIG_RADIUS
                c.bgcolor = None            # gradientを効かせるため下地は消す
                c.gradient = _make_gradient(item.gradient)
                c.border = None
                # c.opacity = 1.0
                icons[i].size = 64
                icons[i].color = "#FFFFFF"
                labels[i].size = 28
                labels[i].color = "#FFFFFF"
                descriptions[i].visible=True
            else:
                # 非選択 → 左列の元の位置・サイズへ。白地に戻す。
                c.left = SMALL_LEFT
                c.top = small_top_for(i)
                c.width = SMALL_WIDTH
                c.height = SMALL_HEIGHT
                c.border_radius = SMALL_RADIUS
                c.gradient = None
                c.bgcolor = Theme.SURFACE
                c.border = ft.border.all(1, Theme.BORDER)
                # 何か選択されている間は薄く、未選択状態なら通常表示
                icons[i].size = 22
                icons[i].color = item.gradient[1]   # 小さい時もその機能の色をアイコンに残す
                labels[i].size = 14
                labels[i].color = Theme.TEXT
                descriptions[i].visible = False

        page.update()


    def make_on_click(index: int):
        """
        クリックハンドラを作る。
        ループ変数をそのままlambdaで捕まえると全カードが最後のindexを
        参照してしまうため、この関数でindexを閉じ込めている。
        """
        def on_click(e):
            if state["selected_index"] == index:
                # 選択中のカードをもう一度クリック → その画面へ遷移
                route = _NAV_ITEMS[index].route
                logger.info("%s へ遷移します", route)
                page.go(route)
            else:
                state["selected_index"] = index
                update_all_positions()
        return on_click

    for i, item in enumerate(_NAV_ITEMS):
        icon = ft.Icon(item.icon, size=22, color=item.gradient[1])
        label = ft.Text(item.label, size=14, weight=ft.FontWeight.BOLD, color=Theme.TEXT)
        # 説明文は拡大時だけ表示する(小さい枠には入りきらないため)
        description = ft.Text(
            item.description, size=14, color="#FFFFFF",
            text_align=ft.TextAlign.CENTER,
            visible=False,
        )

        icons.append(icon)
        labels.append(label)
        descriptions.append(description)

        c = ft.Container(
            content=ft.Column(
                controls=[icon, label, description],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            bgcolor=Theme.SURFACE,
            border=ft.border.all(1, Theme.BORDER),
            border_radius=SMALL_RADIUS,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            padding=8,
            left=SMALL_LEFT,
            top=small_top_for(i),
            width=SMALL_WIDTH,
            height=SMALL_HEIGHT,
            # 位置・サイズ・角丸/色・透明度、それぞれのアニメーション設定
            animate=ft.Animation(350, ft.AnimationCurve.EASE_OUT),
            animate_position=ft.Animation(350, ft.AnimationCurve.EASE_OUT),
            animate_size=ft.Animation(350, ft.AnimationCurve.EASE_OUT),
            on_click=make_on_click(i),
            ink=True,
        )
        containers.append(c)

    stage = ft.Stack(containers, width=STAGE_WIDTH, height=STAGE_HEIGHT)

    def logout(e):
        logger.info("ログアウトしました")
        page.go("/")

    logout_btn = ft.TextButton(
        text="ログアウト",
        icon=ft.Icons.LOGOUT,
        on_click=logout,
        style=ft.ButtonStyle(
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            shape=ft.RoundedRectangleBorder(radius=Theme.RADIUS_SM),
            color=Theme.DANGER,
            icon_color=Theme.DANGER,
        ),
    )

    return ft.View(
        "/index",
        controls=[
            ft.Column(
                controls=[
                    section_title("ホーム", "項目をクリックして選択、もう一度クリックで開きます"),
                    ft.Container(height=16),
                    stage,
                    ft.Container(height=8),
                    ft.Row([logout_btn], alignment=ft.MainAxisAlignment.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            )
        ],
        bgcolor=Theme.BG,
        padding=ft.Padding(left=40, top=24, right=40, bottom=16),
    )