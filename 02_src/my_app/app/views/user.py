"""
ユーザー管理画面(GUI)

ユーザーの一覧表示・氏名/カナ氏名での部分一致検索・
セル上での直接編集(フォーカスが外れた時点で保存)・複数選択削除を行う画面。
"""
import logging
import asyncio
import sqlite3

import flet as ft

import my_app.db.repository as repo
from my_app.app.views.common import (
    show_error_dialog,
    Theme, card, section_title,
    centered_cell, app_view, pager,
    secondary_button, danger_button,
    show_confirm_dialog, show_info_dialog,
    management_tabs,
)

logger = logging.getLogger(__name__)
ITEMS_PER_PAGE = 10


def user_view(page: ft.Page):
    # ===================================================
    # 状態変数
    # ===================================================
    offset = 0                     # 現在のページ番号(0始まり)
    all_page = 1                   # 全ページ数
    search_text = ""               # 検索窓に確定した検索語(空なら全件表示)
    selected_ids = []              # チェックボックスで選択されたuser_idのリスト
    checkbox_refs = {}             # {user_id: Checkboxコントロール} の対応表

    page.title = "ユーザー管理画面"
    page.bgcolor = Theme.BG

    # ===================================================
    # 検索
    # ===================================================

    def search(e=None):
        """検索ボタン/Enter: 検索語を確定して1ページ目から表示する"""
        nonlocal search_text, offset
        search_text = search_box.value.strip()
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
        focused_border_color=Theme.MAUVE,
        border_radius=8,
        prefix_icon=ft.Icons.SEARCH,
        on_submit=search,
    )

    search_button = secondary_button("検索", search, ft.Icons.SEARCH)

    # ===================================================
    # UIコントロールの定義
    # ===================================================

    # リセットボタン定義
    reset_btn = secondary_button(
        "リセット",
        lambda e: page.run_task(refresh, e),
        ft.Icons.REFRESH,
    )

    # 検索欄定義
    search_zone_row = ft.Row(
        controls=[
            search_box,
            search_button,
            reset_btn,
        ],
        spacing=16,
        run_spacing=12,
        wrap=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ページ遷移ボタン定義
    prev_btn = secondary_button(
        "前へ",
        lambda e: prev_page(e),
        ft.Icons.CHEVRON_LEFT,
    )

    page_label = ft.Text("")

    next_btn = secondary_button(
        "次へ",
        lambda e: next_page(e),
        ft.Icons.CHEVRON_RIGHT,
    )

    # ボタン群をまとめて再定義
    btn_zone = pager(prev_btn, page_label, next_btn)

    # テーブル本体, カラムヘッダーの定義
    table = ft.DataTable(
        columns=[
            ft.DataColumn(  # セル中央揃えもcommon.centered_cellに外注
                centered_cell(ft.Text("ID", weight=ft.FontWeight.BOLD), 100),
                on_sort=lambda e: page.run_task(sort_table, e),
            ),
            ft.DataColumn(centered_cell(
                ft.Text("氏名", weight=ft.FontWeight.BOLD), 200)),
            ft.DataColumn(centered_cell(
                ft.Text("カナ氏名", weight=ft.FontWeight.BOLD), 200)),
            ft.DataColumn(centered_cell(
                danger_button("行を削除", lambda e: open_confirm_dialog(e),
                            ft.Icons.DELETE_OUTLINE),
                140
            )),
        ],
        rows=[],
        # sort_column_index=0,  ソート用矢印を最初だけ消すためにコメントアウト
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
    # リセット、ソート関数
    # ===================================================

    async def refresh(e):
        """リセットボタン: 検索条件・並び順・ページを全部初期状態に戻す"""
        nonlocal search_text, offset
        reset_btn.disabled = True
        page.update()

        table.sort_ascending = True
        search_box.value = ""   # 検索窓をクリア
        search_text = ""
        offset = 0
        load_table()
        scroll_table.scroll_to(offset=0, duration=0)

        await asyncio.sleep(0.2)
        reset_btn.disabled = False
        page.update()

    async def sort_table(e):
        """IDカラムのヘッダークリック: 昇順/降順を切り替えて再読込"""
        nonlocal offset
        table.sort_column_index = 0   # 初回クリックでソート矢印を表示する
        table.sort_ascending = not table.sort_ascending
        offset = 0
        load_table()

    # ===================================================
    # ページ遷移関数
    # ===================================================

    def prev_page(e):
        """前ページへ遷移"""
        nonlocal offset
        if offset != 0:
            offset -= 1
        load_table()
        scroll_table.scroll_to(offset=0, duration=0)

    def next_page(e):
        """次ページへ遷移"""
        nonlocal offset
        if (offset + 1) < all_page:
            offset += 1
        load_table()
        scroll_table.scroll_to(offset=0, duration=0)

    # ===================================================
    # テーブル読み込み関数
    # ===================================================

    def load_table():
        """
        検索語(無ければ全件)に基づいてユーザーを取得し、テーブルを再構築する。
        氏名・カナ氏名のセルは編集可能なTextFieldで、フォーカスが外れた時点で
        save_user が呼ばれてDBに保存される。
        """
        nonlocal offset, all_page

        users, total = repo.find_users_with_total(
            search_text,
            table.sort_ascending,
            ITEMS_PER_PAGE,
            offset * ITEMS_PER_PAGE,
        )

        while not users and offset > 0:
            offset -= 1
            users, total = repo.find_users_with_total(
                search_text, table.sort_ascending,
                ITEMS_PER_PAGE, offset * ITEMS_PER_PAGE,
            )

        all_page = max(
            1,
            (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE,
        )

        # 初期化
        checkbox_refs.clear()
        table.rows.clear()

        # 該当ユーザー情報分繰り返し
        for user in users:
            # チェックボックスにユーザーIDを紐づけ
            cb = ft.Checkbox()
            checkbox_refs[user.id] = cb

            # 氏名・カナ氏名は編集可能なTextFieldにする
            name_field = ft.TextField(
                value=user.user_name,
                border=ft.InputBorder.NONE,
                text_align=ft.TextAlign.CENTER,
            )
            kana_field = ft.TextField(
                value=user.user_kana,
                border=ft.InputBorder.NONE,
                text_align=ft.TextAlign.CENTER,
            )

            # フォーカスが外れた時点で保存する。
            # 氏名・カナ氏名どちらの欄から外れても、行(row)の両方の値をまとめて保存する。
            for field in (name_field, kana_field):
                field.on_blur = (
                    lambda e, uid=user.id, n=name_field, k=kana_field:
                    save_user(uid, n, k)
                )

            table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(centered_cell(
                        ft.Text(f"{user.id:05d}", color=Theme.TEXT_MUTED), 100)),
                    ft.DataCell(centered_cell(name_field, 200)),
                    ft.DataCell(centered_cell(kana_field, 200)),
                    ft.DataCell(centered_cell(cb, 140)),
                ])
            )

        # その他項目の設定
        page_label.value = (
            f"{offset + 1} / {all_page} ページ"
            f"（全{total}件）"
        )
        prev_btn.disabled = offset == 0
        next_btn.disabled = (offset + 1) >= all_page
        page.update()

    def save_user(user_id, name_field, kana_field):
        """
        セルの編集内容をDBに保存する(フォーカスが外れた時点で呼ばれる)。
        """
        try:
            repo.update_user(user_id, name_field.value, kana_field.value)
            logger.info(f"user_id={user_id}を更新しました")
        except sqlite3.Error:
            logger.exception("ユーザー情報の更新に失敗しました: user_id=%s", user_id)
            show_error_dialog(page, "変更の保存に失敗しました。しばらくしてから再度お試しください")
            load_table()   # 保存できていないので、DBの内容に戻す

    # ===================================================
    # 削除
    # ===================================================

    def open_confirm_dialog(e):
        """「行を削除」クリック: チェック済みの行を確認してから削除ダイアログを開く"""
        nonlocal selected_ids
        selected_ids = [uid for uid, cb in checkbox_refs.items() if cb.value]

        if not selected_ids:
            show_info_dialog(page, "削除する行が選択されていません", title="削除の確認")
            return

        show_confirm_dialog(
            page,
            f"{len(selected_ids)} 件を削除しますか?\n"
            f"(このユーザーのカード・顔情報も一緒に削除されます)",
            on_confirm=confirm_delete,
            title="削除の確認",
        )

    def confirm_delete():
        """
        削除確定: 選択されたuser_idを1件ずつ repo.delete_user に渡す。
        card / face は外部キーのCASCADEで一緒に削除される。
        """
        try:
            for user_id in selected_ids:
                repo.delete_user(user_id)
                logger.info(f"user_id={user_id}が削除されました")
        except sqlite3.Error:
            logger.exception("ユーザー情報の削除に失敗しました")
            show_error_dialog(page, "削除に失敗しました。しばらくしてから再度お試しください")
            load_table()   # 途中まで消えている可能性があるので一覧を最新化しておく
            return

        load_table()

        refresh_tabs = getattr(
            page,
            "_refresh_management_tabs",
            None,
        )

        if callable(refresh_tabs):
            refresh_tabs()

        show_info_dialog(page, f"{len(selected_ids)} 件を削除しました", title="削除完了")

    # ===================================================
    # レイアウト定義、実際に配置
    # ===================================================

    # データテーブルはそのままだと中央揃えできないためRow化
    table_row = ft.Row(
        [table],
        alignment=ft.MainAxisAlignment.CENTER,
    )

    # スクロール可能の定義
    scroll_table = ft.Column(
        controls=[table_row],
        scroll=ft.ScrollMode.HIDDEN,
        expand=True,
    )

    # テーブル読み込み
    load_table()

    # ===================================================
    # commonスタイル適用
    # ===================================================

    # 検索欄用カード(土台のパネル)
    search_card = card(
        ft.Column(
            controls=[
                section_title(
                    "ユーザー検索",
                    accent=Theme.MAUVE,
                ),
                ft.Container(height=6),
                search_zone_row,
            ],
            spacing=10,
        ),
        accent=Theme.MAUVE,
    )

    # テーブル用カード(土台のパネル)
    table_card = card(
        ft.Column(
            controls=[
                section_title(
                    "ユーザー一覧",
                    accent=Theme.MAUVE,
                ),
                ft.Container(height=10),
                scroll_table,
                ft.Container(height=10),
                btn_zone,
            ],
            spacing=10,
            expand=True,
        ),
        accent=Theme.MAUVE,
    )

    # ===================================================
    # 実際にページに
    # ===================================================

    return app_view(
        "/user",
        page,
        [
            management_tabs(page, "/user"),
            search_card,
            ft.Container(height=16),
            table_card,
        ],
        back_route="/index",
    )