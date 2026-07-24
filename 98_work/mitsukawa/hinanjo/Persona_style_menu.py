import flet as ft

# ==========================================
# レイアウトサイズの定数
# ==========================================
STAGE_WIDTH = 600
STAGE_HEIGHT = 420

SMALL_WIDTH = 160
SMALL_HEIGHT = 110
SMALL_LEFT = 20          # 左列のx位置
SMALL_TOP_START = 20     # 一番上のアイテムのy位置
SMALL_GAP = 20           # アイテム同士の縦の間隔

BIG_WIDTH = 340
BIG_HEIGHT = 380
BIG_LEFT = 240           # 右の大きな枠のx位置
BIG_TOP = 20

SMALL_RADIUS = 14        # 小さい時の角丸
BIG_RADIUS = 28          # 大きい時の角丸(サイズに見合った大きさに)


def main(page: ft.Page):
    page.title = "選択で拡大移動するメニュー"
    page.bgcolor = ft.Colors.WHITE
    page.window.width = 680
    page.window.height = 500
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    state = {"selected_index": None}

    items = [
        {"label": "カード登録", "icon": ft.Icons.CREDIT_CARD, "color": ft.Colors.RED_400},
        {"label": "ログ確認", "icon": ft.Icons.HISTORY, "color": ft.Colors.BLUE_400},
        {"label": "顔認証設定", "icon": ft.Icons.FACE, "color": ft.Colors.GREEN_400},
    ]

    containers = []
    labels = []  # 拡大時に文字サイズも変えたいのでTextを個別に参照しておく

    def small_top_for(index):
        # 未選択時、縦に並べた時のy位置
        return SMALL_TOP_START + index * (SMALL_HEIGHT + SMALL_GAP)

    def update_all_positions():
        for i, c in enumerate(containers):
            label_text = labels[i]
            if state["selected_index"] == i:
                # 選択中 → 右の大きな枠の位置・サイズへ
                c.left = BIG_LEFT
                c.top = BIG_TOP
                c.width = BIG_WIDTH
                c.height = BIG_HEIGHT
                c.border_radius = BIG_RADIUS
                c.opacity = 1.0
                label_text.size = 22
            else:
                # 非選択 → 左列の元の位置・サイズへ戻す
                c.left = SMALL_LEFT
                c.top = small_top_for(i)
                c.width = SMALL_WIDTH
                c.height = SMALL_HEIGHT
                c.border_radius = SMALL_RADIUS
                # 何か選択されている間は薄く、未選択状態なら通常表示
                c.opacity = 0.35 if state["selected_index"] is not None else 1.0
                label_text.size = 14
        page.update()

    def go_to_screen(index):
        print(f"{items[index]['label']} の画面へ遷移します")

    def make_on_click(index):
        def on_click(e):
            if state["selected_index"] == index:
                go_to_screen(index)
            else:
                state["selected_index"] = index
                update_all_positions()
        return on_click

    for i, item in enumerate(items):
        label = ft.Text(
            item["label"],
            size=14,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.WHITE,
        )
        labels.append(label)

        card = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(item["icon"], size=32, color=ft.Colors.WHITE),
                    label,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=item["color"],
            border_radius=SMALL_RADIUS,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            padding=15,
            left=SMALL_LEFT,
            top=small_top_for(i),
            width=SMALL_WIDTH,
            height=SMALL_HEIGHT,
            opacity=1.0,
            # 位置・サイズ・角丸・透明度、それぞれのアニメーション設定
            animate=ft.Animation(350, ft.AnimationCurve.EASE_OUT),          # border_radius用
            animate_position=ft.Animation(350, ft.AnimationCurve.EASE_OUT),
            animate_size=ft.Animation(350, ft.AnimationCurve.EASE_OUT),
            animate_opacity=ft.Animation(250, ft.AnimationCurve.EASE_OUT),
            on_click=make_on_click(i),
            ink=True,
        )
        containers.append(card)

    stage = ft.Stack(
        containers,
        width=STAGE_WIDTH,
        height=STAGE_HEIGHT,
    )

    hint_text = ft.Text(
        "項目をタップして選択、もう一度タップで決定",
        size=13,
        color=ft.Colors.GREY_600,
    )

    page.add(
        ft.Column(
            [stage, ft.Container(height=15), hint_text],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )


ft.app(target=main)