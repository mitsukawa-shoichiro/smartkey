"""
カード管理画面(GUI)

カード情報(card)の一覧表示・ユーザー名でのプルダウン検索・
ページ更新・複数選択削除を行う画面。共通部分はcommon.pyへ切り出し!
sho
"""
import logging
import asyncio
import sqlite3
import flet as ft
import my_app.db.repository as repo
from my_app.models.ENUMS import CardType
from my_app.app.utils.pagination import Pagination
from my_app.app.views.common import (
    show_error_dialog,
    Theme, card, section_title, card_type_badge,
    centered_cell, app_view, empty_state, pager,
    secondary_button, danger_button,
    show_confirm_dialog, show_info_dialog,
    management_tabs,
)

logger = logging.getLogger(__name__)
ITEMS_PER_PAGE = 10

# 列幅定義、ヘッダーと行はここを参照する
_W = {
    "id": 100,
    "type": 140,
    "date": 140,
    "user": 140,
    "delete": 140,
}

def _build_card_row(card, checkbox) -> ft.DataRow:
    """
    一件のカード情報からテーブル一行を組み立てるビルダー
    Args:
        card (Card): カード情報(データクラス)
        checkbox (ft.CheckBox): IDと紐づくチェックボックスオブジェクト

    Returns:
        ft.DataRow: _description_
    """
    return ft.DataRow(cells=[
        ft.DataCell(centered_cell(ft.Text(f"{card.id:05d}", color=Theme.TEXT_MUTED), _W["id"])),
        ft.DataCell(centered_cell(card_type_badge(card.card_type.value), _W["type"])),
        ft.DataCell(centered_cell(ft.Text(str(card.register_date), color=Theme.TEXT_MUTED), _W["date"])),
        ft.DataCell(centered_cell(ft.Text(card.user_name or "(未設定)"), _W["user"])),
        ft.DataCell(centered_cell(checkbox, _W["delete"])),
    ])

def cardView(page: ft.Page):
    # ===================================================
    # 状態変数
    # ===================================================
    offset = 0                     # 現在のページ番号(0始まり)
    all_page = 1                   # 全ページ数
    selected_user_id = None        # プルダウンで選択中のユーザーID(未選択ならNone=全件表示)
    selected_ids = []              # チェックボックスで選択されたcard_idのリスト
    checkbox_refs = {}             # {card_id: Checkboxコントロール} の対応表

    page.title = "カード管理画面"
    page.bgcolor = Theme.BG

    # ===================================================
    # ユーザー検索用プルダウンの候補データ
    # ===================================================
    # 画面表示のたびに最新のユーザー一覧を取得する
    try:
        users = repo.get_all_users()
    except sqlite3.Error :
        logger.error("ユーザー情報取得エラー")
        show_error_dialog(page, "必要情報の取得に失敗しました", go_home=True)
        return ft.View("/user", controls=[])

    def on_user_selected(user_id: int):
        """Autocompleteでユーザーが選択された時: そのuser_idで絞り込み検索する"""
        nonlocal selected_user_id, offset
        selected_user_id = user_id
        offset = 0
        load_table()
        scroll_table.scroll_to(offset=0, duration=0)

    search_box = ft.TextField(
        label="氏名・カナ氏名",
        hint_text="部分一致検索",
        width=320,
        height=52,
        filled=True,
        fill_color=Theme.SURFACE,
        border_color=Theme.BORDER,
        focused_border_color=Theme.MINT,
        border_radius=8,
        prefix_icon=ft.Icons.SEARCH,
        on_submit=search,
    )

    search_button = secondary_button(
        "検索",
        search,
        ft.Icons.SEARCH,
    )

    reset_btn = secondary_button(
        "リセット",
        lambda e: page.run_task(refresh, e),
        ft.Icons.REFRESH,
    )

    search_zone_row = ft.Row(
        controls=[
            search_box,
            search_button,
            reset_btn,
        ],
        spacing=16,
        wrap=True,
        run_spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


    # ===================================================
    # UIコントロールの定義
    # ===================================================

    # ページ遷移ボタン定義
    prev_btn = secondary_button(
        "前へ",
        lambda e: prev_page(e),
        ft.Icons.CHEVRON_LEFT
    )

    page_label = ft.Text("")

    next_btn = secondary_button(
        "次へ",
        lambda e: next_page(e),
        ft.Icons.CHEVRON_RIGHT
    )

    # ボタン群をまとめて再定義
    btn_zone = pager(prev_btn, page_label, next_btn)

    # テーブル本体, カラムヘッダーの定義
    table = ft.DataTable(
        columns=[
            ft.DataColumn( # セル中央揃えもcommon.centered_cellに外注
                centered_cell(ft.Text("ID", weight=ft.FontWeight.BOLD), _W["id"]),
                on_sort=lambda e: page.run_task(sort_table, e),
            ),
            ft.DataColumn(
                centered_cell(
                    ft.Text("カードの種類", weight=ft.FontWeight.BOLD), _W["type"]
                )
            ),
            ft.DataColumn(
                centered_cell(
                    ft.Text("登録日", weight=ft.FontWeight.BOLD), _W["date"]
                )
            ),
            ft.DataColumn(
                centered_cell(
                    ft.Text("ユーザー名", weight=ft.FontWeight.BOLD), _W["user"]
                )
            ),
            ft.DataColumn(
                centered_cell(
                    danger_button("行を削除", lambda e: open_confirm_dialog(e), ft.Icons.DELETE_OUTLINE), _W["delete"]
                )
            ),
        ],

        rows=[],
        #sort_column_index=0, ソート用矢印を最初だけ消すためにコメントアウト

        # 各種設定
        sort_ascending=True,
        heading_row_color=Theme.HEADING_BG,
        heading_row_height=48,
        data_row_min_height=52,
        data_row_max_height=52,
        divider_thickness=1,
        horizontal_lines=ft.BorderSide(1, Theme.BORDER),
        column_spacing=20,
    )



    # ===================================================
    # 更新、ソート関数
    # ===================================================

    async def refresh(e):
        """リセットボタン: 検索条件・並び順・ページを全部初期状態に戻す"""
        nonlocal selected_user_id, offset, reset_btn, user_search
        reset_btn.disabled = True
        page.update()

        search_box.value = ""
        search_text = ""
        table.sort_ascending = True
        offset = 0

        # プルダウンはvalueだけリセットしても表示が変わらないので都度作り直し
        user_search = build_user_autocomplete(users, on_user_selected)
        search_zone.controls = [user_search]
        search_zone.update()

        # リセットした状態でテーブルを読み直す
        load_table()
        scroll_table.scroll_to(offset=0, duration=0)

        await asyncio.sleep(0.2)
        reset_btn.disabled = False
        page.update()

    async def sort_table(e):
        """IDカラムのヘッダークリック: 昇順/降順を切り替えて再読込"""
        table.sort_column_index = 0
        table.sort_ascending = not table.sort_ascending
        pg.reset()
        # ここは処理が重いのか何なのかついていたもの、ちかちかするのでコメントアウト
        # scroll_table.visible = False
        # scroll_table.update()
        # await asyncio.sleep(0.01)
        # scroll_table.visible = True
        # scroll_table.update()
        load_table()

    # ===================================================
    # ページ遷移関数
    # ===================================================

    def prev_page(e):
        if pg.prev():
            load_table()
            scroll_table.scroll_to(offset=0, duration=0)

    def next_page(e):
        if pg.next():
            load_table()
            scroll_table.scroll_to(offset=0, duration=0)

    # ===================================================
    # テーブル読み込み関数
    # ===================================================

    def load_table():
        """
        選択中のuser_id(無ければ全件)に基づいてカード情報を取得し、
        テーブル・チェックボックスを再構築します。
        """
        nonlocal selected_user_id, offset, all_page

        try:
            #全検索の場合
            if selected_user_id is None:
                cards = repo.find_all_cards(table.sort_ascending, offset * 100)
                total = repo.count_all_card()
            # 条件検索の場合
            else:
                cards = repo.find_cards_by_user_id(
                    selected_user_id, table.sort_ascending, offset * 100)
                total = repo.count_cards_by_user_id(selected_user_id)
        except sqlite3.Error:
            logger.exception("カード情報の読み込みに失敗しました")
            show_error_dialog(page, "カード情報の取得に失敗しました。しばらくしてから再度お試しください。")
            return

        #諸パラメータ更新
        all_page = int(((total - 1) / 100) + 1)

        checkbox_refs.clear()
        table.rows.clear()
        column.controls.clear()
        column.controls.append(ft.Container(height=-2))

        # 該当カード情報分繰り返し
        for card in cards:
            # チェックボックスにID埋め込み
            cb = ft.Checkbox()
            checkbox_refs[card.id] = cb

            table.rows.append(_build_card_row(card, cb))

        page_label.value = f"{offset + 1} / {all_page} ページ"
        prev_btn.disabled = offset == 0
        next_btn.disabled = (offset + 1) == all_page
        page.update()

    # ===================================================
    # 削除
    # ===================================================

    def open_confirm_dialog(e):
        nonlocal selected_ids

        selected_ids = [
            card_id
            for card_id, checkbox in checkbox_refs.items()
            if checkbox.value
        ]

        if not selected_ids:
            show_info_dialog(
                page,
                "削除する行が選択されていません。",
                title="削除の確認",
            )
            return

        show_confirm_dialog(
            page,
            f"{len(selected_ids)} 件を削除しますか?",
            on_confirm=confirm_delete,
            title="削除の確認",
        )

    def confirm_delete(e):
        """
        削除確定: 選択されたcard_idを1件ずつ repo.delete_card に渡します。
        """
        try:
            for card_id in selected_ids:
                repo.delete_card(card_id)
                logger.info(
                    "card_id=%sが削除されました",
                    card_id,
                )
        except sqlite3.Error:
            logger.exception("カード情報の削除に失敗しました")
            page.close(dialog)
            show_error_dialog(page, "削除に失敗しました。しばらくしてから再度お試しください。")
            load_table()  # 途中まで消えている可能性があるので一覧を最新化しておく
            return

        load_table()

        show_info_dialog(
            page,
            f"{len(selected_ids)} 件を削除しました。",
            title="削除完了",
        )

    # ===================================================
    # レイアウト定義と配置
    # ===================================================

    # データテーブルはそのまま中央ぞろえできないので一回Row化
    table_row = ft.Row(
        [table],
        alignment=ft.MainAxisAlignment.CENTER,
    )

    # スクロール化
    scroll_table = ft.Column(
        controls=[table_row],
        scroll=ft.ScrollMode.HIDDEN,
        expand=True,
    )

    #テーブル読み込み
    load_table()

    # ===================================================
    # commonスタイル適用
    # ===================================================

    # 検索欄用カード(土台のパネル)
    search_card = card(
        ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            expand=True,
                            content=section_title(
                                "カード検索",
                                accent=Theme.MINT,
                            ),
                        ),
                        primary_button(
                            "カードを登録",
                            lambda e: page.go("/register"),
                            ft.Icons.ADD_CARD,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=6),
                search_zone_row,
            ],
            spacing=10,
        ),
        accent=Theme.MINT,
    )

    # テーブル用カード(土台のパネル)
    table_card = card(
        ft.Column(
            controls=[
                section_title(
                    "カード一覧",
                    accent=Theme.MINT,
                ),
                ft.Container(height=10),
                scroll_table,
                ft.Container(height=10),
                btn_zone,
            ],
            spacing=10,
            expand=True,
        ),
        accent=Theme.MINT,
    )

    # ===================================================
    # 実際にページに
    # ===================================================
    # ここまでdef cardViewの関数
    return app_view(
        "/card",
        page,
        [
            management_tabs(page, "/card"),
            search_card,
            ft.Container(height=16),
            table_card,
        ],
        back_route="/index",
    )