"""
入退室履歴管理画面(GUI)

入退室履歴の一覧表示・ユーザー(プルダウン選択)/認証方式/入退室区分/日時での
絞り込み検索・ページ遷移を行う画面。

削除されたユーザーのログも表示できるよう、access_logs自体にログ記録時点の
ユーザー名(user_name)をスナップショットとして持たせている。
"""
from datetime import datetime, date, time, timedelta
import logging
import sqlite3

import flet as ft

import my_app.db.repository as repo
from my_app.models.ENUMS import EventType
from my_app.app.utils.pagination import Pagination
from my_app.app.views.common import (
    show_error_dialog, build_user_autocomplete,
    Theme, card, section_title,
    centered_cell, app_view, pager,
    secondary_button, badge,
    BADGE_BLUE, BADGE_GREEN, BADGE_ORANGE, BADGE_GRAY,
)

logger = logging.getLogger(__name__)

# 認証方式ごとのバッジ色(未知の方式はグレーにフォールバック)
_METHOD_COLORS = {
    "カード": BADGE_BLUE,
    "顔認証": BADGE_GRAY,
}

# 列幅定義、ヘッダーと行はここを参照する
_W = {
    "label": 260,
    "method": 120,
    "timestamp": 180,
    "event": 100,
}

def _build_log_row(log) -> ft.DataRow:
    """ログ1件をテーブルの1行として組み立てる"""
    is_entry = log.event_type == EventType.ENTRY
    event_str = "入室" if is_entry else "退室"
    event_colors = BADGE_GREEN if is_entry else BADGE_ORANGE

    user_label = log.user_name or "(削除済みユーザー)"
    label = f"{user_label} / {log.card_type}" if log.card_type else user_label

    method_colors = _METHOD_COLORS.get(log.method, BADGE_GRAY)

    return ft.DataRow(cells=[
        ft.DataCell(centered_cell(ft.Text(label), _W["label"])),
        ft.DataCell(centered_cell(badge(log.method, method_colors), _W["method"])),
        ft.DataCell(centered_cell(
            ft.Text(str(log.timestamp), color=Theme.TEXT_MUTED), _W["timestamp"])),
        ft.DataCell(centered_cell(badge(event_str, event_colors), _W["event"])),
    ])


def _validate_search_period(start_str, end_str, first_date, last_date):
    """
    受け取った文字列にチェックをかける関数
    成功時は先頭二つに開始・終了日時が入り、エラー時は最後尾にエラーメッセージが入る

    Args:
        start_text (str): 絞り込み開始日時文字列
        end_text (str): 絞り込み終了日時文字列
        first_date (date): 検索の下限(一年前)
        last_date (date): 検索の上限(今日)

    Returns:
        date, date, str:開始日時、終了日時、エラーメッセージ
    """
    start_dt = None
    end_dt = None
    try:
        # 開始日時が入力された場合はフォーマットに直す(秒数は00秒)
        if start_str:
            start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            start_dt = start_dt.replace(second=0)

        # 終了日時が入力された場合はフォーマットに直す(秒数は59秒)
        if end_str:
            end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M")
            end_dt = end_dt.replace(second=59)

        # 終了日時が開始日時より前
        if start_dt and end_dt and end_dt < start_dt:
            return None, None, "終了日時が開始日時以降にされていません。"


        # 開始日時が範囲外
        if start_dt and (start_dt.date() < first_date or start_dt.date() > last_date):
            return None, None, (
                f"開始日時が範囲外です。\n検索範囲は {first_date.strftime('%Y-%m-%d 00:00')} から"
                f"{last_date.strftime('%Y-%m-%d 23:59')} までです。"
            )


        # 終了日時が範囲外
        if end_dt and (end_dt.date() > last_date or end_dt.date() < first_date):
            return None, None, (
                f"終了日時が範囲外です。\n検索範囲は {first_date.strftime('%Y-%m-%d 00:00')} から"
                f"{last_date.strftime('%Y-%m-%d 23:59')} までです。"
            )

        return start_dt, end_dt, None

    except ValueError:
        return None, None, "日時のフォーマットが正しくありません。"


def access_logs(page: ft.Page):
    page.title = "ログ閲覧画面"
    page.bgcolor = Theme.BG

    # ===================================================
    # 状態変数
    # ===================================================
    pg = Pagination(100)           # ページング状態管理クラス
    selected_user_id = None    # プルダウンで選択中のユーザーID(未選択ならNone=全ユーザー対象)
    search_params = {          # 検索条件を保持(検索ボタン押下時にまとめて確定させる)
        "user_id": None,
        "method": None,
        "event_type": None,
        "start_dt": None,
        "end_dt": None,
    }

    page.locale_configuration = ft.LocaleConfiguration(
        supported_locales=[ft.Locale("ja", "JP"), ft.Locale("en", "US")],
        current_locale=ft.Locale("ja", "JP")
    )

    # ===================================================
    # ユーザー検索用プルダウンの候補データ
    # ===================================================

    # 画面表示のたびに最新のユーザー一覧を取得する

    users = repo.get_all_users()

    def on_user_selected(user_id: int):
        """
        プルダウンでユーザーが選択された時: user_idだけ保持しておく。
        他の検索条件(認証方式・入退室区分・日時)と同様、実際の検索は
        検索ボタン押下時(search_logs)にまとめて確定させる。
        """
        nonlocal selected_user_id
        selected_user_id = user_id

    search_user = build_user_autocomplete(users, on_user_selected)

    # プルダウンはvalueだけリセットしても表示が変わらないため、
    # リセット時はこのRowの中身を作り直して差し替える
    search_zone = ft.Row(controls=[search_user], spacing=0)

    # ===================================================
    # 日付ピッカー関連
    # ===================================================

    def change_start_date(e):
        if start_date.value:
            start_time.open = True
            open_timepicker(start_time)
            page.update()

    def change_end_date(e):
        if end_date.value:
            end_time.open = True
            open_timepicker(end_time)
            page.update()

    def open_datepicker(picker: ft.DatePicker):
        page.dialog = picker
        picker.open = True
        page.update()

    def open_timepicker(picker: ft.TimePicker):
        page.dialog = picker
        picker.open = True
        page.update()

    def update_start_textbox():
        """日時ピッカーの値をテキストボックスに反映(日付・時刻どちらも入力された場合のみ)"""
        if start_date.value and start_time.value:
            dt = datetime.combine(start_date.value, start_time.value)
            start_text.value = dt.strftime("%Y-%m-%d %H:%M")
        else:
            start_text.value = ""
        page.update()

    def update_end_textbox():
        if end_date.value and end_time.value:
            dt = datetime.combine(end_date.value, end_time.value)
            end_text.value = dt.strftime("%Y-%m-%d %H:%M")
        else:
            end_text.value = ""
        page.update()

    # ===================================================
    # 検索フィールドの定義
    # ===================================================

    # 認証方式の選択
    method_dropdown = ft.DropdownM2(label="認証方式", value=None, width=120, height=48)
    method_dropdown.options = [
        ft.DropdownOption("カード", "カード"),
        ft.DropdownOption("顔認証", "顔認証"),
    ]

    # 入退室区分
    search_eventtype = ft.DropdownM2(label="入室/退室", value=None, width=120, height=48)
    search_eventtype.options = [
        ft.DropdownOption("1", "入室"),
        ft.DropdownOption("0", "退室"),
    ]

    today = date.today()

    start_date = ft.DatePicker(
        on_change=change_start_date, date_picker_entry_mode=ft.DatePickerEntryMode.INPUT,
        first_date=today - timedelta(days=365), last_date=today
    )
    end_date = ft.DatePicker(
        on_change=change_end_date, date_picker_entry_mode=ft.DatePickerEntryMode.INPUT,
        first_date=today - timedelta(days=365), last_date=today
    )
    start_time = ft.TimePicker(
        value=time(0, 0), on_change=lambda e: update_start_textbox(),
        time_picker_entry_mode=ft.TimePickerEntryMode.INPUT
    )
    end_time = ft.TimePicker(
        value=time(23, 59), on_change=lambda e: update_end_textbox(),
        time_picker_entry_mode=ft.TimePickerEntryMode.INPUT
    )

    start_text = ft.TextField(label="開始日時", width=200, height=48)
    end_text = ft.TextField(label="終了日時", width=200, height=48)

    # ===================================================
    # 検索実行
    # ===================================================

    def search_logs(e):
        """
        検索ボタン: 各検索欄(ユーザー・認証方式・入退室区分・日時)の値を
        まとめてsearch_paramsに確定させ、1ページ目から検索結果を表示する。
        """
        nonlocal search_params

        search_method = method_dropdown.value.strip() if method_dropdown.value else None
        search_event_type = int(search_eventtype.value.strip()) if search_eventtype.value else None

        first_date = today - timedelta(days=365)
        last_date = today

        start_dt, end_dt, error_message = _validate_search_period(start_text.value, end_text.value, first_date, last_date)
        if error_message:
            show_error_dialog(page, error_message)
            return

        search_params = {
            "user_id": selected_user_id,
            "method": search_method,
            "event_type": search_event_type,
            "start_dt": start_dt,
            "end_dt": end_dt,
        }

        pg.reset()

        load_table()
        scroll_table.scroll_to(offset=0, duration=0)

    # ===================================================
    # ソート
    # ===================================================

    async def on_sort(e):
        """日時カラムのヘッダークリック: 昇順/降順を切り替えて再読込"""
        table.sort_column_index = 2   # 初回クリックでソート矢印を表示する
        table.sort_ascending = not table.sort_ascending
        pg.reset()
        load_table()

    # ===================================================
    # 全件表示・リセット
    # ===================================================

    def show_all_logs(e):
        """全件検索してテーブルに表示(検索条件を全てクリアする)"""
        nonlocal search_params
        search_params = {
            "user_id": None, "method": None, "event_type": None,
            "start_dt": None, "end_dt": None,
        }
        pg.reset()
        reset(e)
        load_table()

    def reset(e):
        """検索欄のリセット(ユーザー選択も含む)"""
        nonlocal selected_user_id, search_user
        selected_user_id = None

        # プルダウンはvalueだけリセットしても表示が変わらないので都度作り直し
        search_user = build_user_autocomplete(users, on_user_selected)
        search_zone.controls = [search_user]
        search_zone.update()

        method_dropdown.value = None
        search_eventtype.value = None
        start_text.value = ""
        end_text.value = ""
        start_date.value = None
        end_date.value = None
        start_time.value = time(0, 0)
        end_time.value = time(23, 59)
        page.update()

    start_date.on_change = change_start_date
    end_date.on_change = change_end_date

    # ===================================================
    # ボタン定義
    # ===================================================

    page_label = ft.Text("")  # load_table内で更新

    prev_btn = secondary_button("⬅ 前へ", lambda e: prev_page(e))
    next_btn = secondary_button("次へ ➡", lambda e: next_page(e))
    pagination_controls = pager(prev_btn, page_label, next_btn)

    search_btn = ft.ElevatedButton(
        text="検索", icon=ft.Icons.SEARCH, on_click=search_logs,
        bgcolor=Theme.PRIMARY, color="#FFFFFF", height=44,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=Theme.RADIUS_SM),
            padding=ft.padding.symmetric(horizontal=20),
        ),
    )
    show_all_btn = secondary_button("全件表示", show_all_logs)
    reset_btn = secondary_button("クリア", reset)
    start_date_btn = secondary_button(
        "開始日時を選択", lambda e: open_datepicker(start_date), ft.Icons.DATE_RANGE)
    end_date_btn = secondary_button(
        "終了日時を選択", lambda e: open_datepicker(end_date), ft.Icons.DATE_RANGE)

    # ===================================================
    # テーブル定義
    # ===================================================

    table = ft.DataTable(
        columns=[
            ft.DataColumn(centered_cell(
                ft.Text("ユーザー名 / カード種別", weight=ft.FontWeight.BOLD), _W["label"])),
            ft.DataColumn(centered_cell(
                ft.Text("認証方式", weight=ft.FontWeight.BOLD), _W["method"])),
            ft.DataColumn(
                centered_cell(ft.Text("入退室の日時", weight=ft.FontWeight.BOLD), _W["timestamp"]),
                on_sort=lambda e: page.run_task(on_sort, e),
            ),
            ft.DataColumn(centered_cell(
                ft.Text("区分", weight=ft.FontWeight.BOLD), _W["event"])),
        ],
        rows=[],
        # sort_column_index=2,  ソート矢印を最初だけ消すためコメントアウト(初回クリックで設定)
        sort_ascending=False,
        heading_row_color=Theme.HEADING_BG,
        heading_row_height=48,
        data_row_min_height=52,
        data_row_max_height=52,
        divider_thickness=1,
        horizontal_lines=ft.BorderSide(1, Theme.BORDER),
        column_spacing=20,
    )

    # ==================================================
    # テーブル読み込み関数
    # ==================================================

    def load_table():
        """
        search_params(検索条件)に基づいてログを取得し、テーブルへ反映する。
        """
        try:
            logs, total = repo.find_access_logs_with_total(
                search_params["method"], search_params["event_type"],
                search_params["start_dt"], search_params["end_dt"],
                pg.per_page, pg.offset, search_params["user_id"],
                table.sort_ascending,
            )
        except sqlite3.Error:
            logger.exception("ログの読み込みに失敗しました")
            show_error_dialog(page, "ログの取得に失敗しました。しばらくしてから再度お試しください。")
            return

        pg.update_total(total)

        table.rows.clear()

        for log in logs:
            table.rows.append(_build_log_row(log))

        page_label.value = pg.label
        prev_btn.disabled = pg.is_first
        next_btn.disabled = pg.is_last
        page.update()

    # ===================================================
    # ページ送り
    # ===================================================

    def next_page(e):
        if pg.next():
            load_table()
            scroll_table.scroll_to(offset=0, duration=0)

    def prev_page(e):
        if pg.prev():
            load_table()
            scroll_table.scroll_to(offset=0, duration=0)

    # ===================================================
    # レイアウト
    # ===================================================

    page.overlay.append(start_date)
    page.overlay.append(end_date)
    page.overlay.append(start_time)
    page.overlay.append(end_time)

    # データテーブルはそのままだと中央揃えできないためRow化
    table_row = ft.Row([table], alignment=ft.MainAxisAlignment.CENTER)
    scroll_table = ft.Column(controls=[table_row], scroll=ft.ScrollMode.ALWAYS, expand=True)

    # 検索条件エリア(トグルで開閉)
    search_area = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row([search_zone, method_dropdown, search_eventtype, reset_btn],
                    spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([start_date_btn, start_text, end_date_btn, end_text],
                    spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([search_btn, show_all_btn], spacing=16),
            ],
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        ),
        padding=ft.padding.only(top=16),
        visible=False,
    )

    def toggle_search_area(e):
        search_area.visible = not search_area.visible
        toggle_btn.text = "検索オプションを閉じる" if search_area.visible else "検索オプションを開く"
        page.update()

    toggle_btn = secondary_button("検索オプションを開く", toggle_search_area, ft.Icons.TUNE)

    # ===================================================
    # commonスタイル適用
    # ===================================================

    # 検索欄用カード(土台のパネル)
    search_card = card(
        ft.Column(
            controls=[
                section_title("入退室ログ"),
                ft.Container(height=4),
                toggle_btn,
                search_area,
            ],
            spacing=8,
        )
    )

    # テーブル用カード(土台のパネル)
    table_card = card(
        ft.Column(
            controls=[
                section_title("ログ一覧"),
                ft.Container(height=8),
                scroll_table,
                ft.Container(height=8),
                pagination_controls,
            ],
            spacing=8,
            expand=True,
        )
    )

    # 初回の読み込み(全件モード)
    load_table()

    # ===================================================
    # 実際にページに
    # ===================================================

    return app_view("/access_logs", page, [
        search_card,
        ft.Container(height=16),
        table_card,
    ])