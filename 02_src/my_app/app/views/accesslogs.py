from datetime import datetime
from datetime import time
import flet as ft
import app.models.db_manager as db

ITEMS_PER_PAGE = 100

# ログ閲覧画面
def accesslogs(page: ft.Page):

    current_page = 0           # 現在のページ（0‑origin）
    total_pages = 1            # 総ページ数（動的に計算）
    search_mode = False        # False: 全件モード / True: 検索モード
    search_params = {          # 検索条件を保持
        "card_name": None,
        "method": None,
        "eventtype": None,
        "start_dt": None,
        "end_dt": None,
    }
    
    start_text = ft.TextField(label="開始日時", width=200, height=48)
    end_text = ft.TextField(label="終了日時", width=200, height=48)
    
    dialog = ft.AlertDialog(
        modal=True,
    )
    def calc_total_pages(count: int):
        nonlocal total_pages
        total_pages = max(1, (count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    # 日付の入力値を変換するフォーマット
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

    # 日付入力のロケール設定
    page.locale_configuration = ft.LocaleConfiguration(
        supported_locales=[
            ft.Locale("ja", "JP"),
            ft.Locale("en", "US")
        ], 
        current_locale=ft.Locale("ja", "JP")
    )
    
    page.title = "ログ閲覧画面"

    # 検索フィールドの定義
    searchcardname = ft.TextField(label="カード名",width=200,height=48)
    searchmethod = ft.DropdownM2(label="認証   方式",value=None,width=85,height=45)
    searchmethod.options = [
        ft.DropdownOption("カード", "カード"),
        ft.DropdownOption("Web", "Web"),
    ]
    
    start_date = ft.DatePicker(on_change=change_start_date)
    end_date = ft.DatePicker(on_change=change_end_date)

    start_time = ft.TimePicker(value=time(0, 0), on_change=lambda e: update_start_textbox())
    end_time = ft.TimePicker(value=time(23, 59), on_change=lambda e: update_end_textbox())

    searcheventtype = ft.DropdownM2(label="入室/  退室",value=None,width=85,height=45)
    searcheventtype.options = [
        ft.DropdownOption("0", "入室"),
        ft.DropdownOption("1", "退室"),
    ]
        
    # 検索結果を表示するためのテーブル
    def search_logs(e):
        nonlocal current_page, search_mode, search_params
        
        search_method = searchmethod.value.strip() if searchmethod.value else None
        search_cardname = searchcardname.value.strip() if searchcardname.value else None
        search_eventtype = int(searcheventtype.value.strip()) if searcheventtype.value else None
        start_dt = None
        end_dt = None
        
        if start_text.value != "" and end_text.value != "":
            start_dt = datetime.strptime(start_text.value, "%Y-%m-%d %H:%M")
            start_dt = start_dt.replace(second=0)
            end_dt = datetime.strptime(end_text.value, "%Y-%m-%d %H:%M")
            end_dt = end_dt.replace(second=59)

            if start_dt and end_dt and end_dt < start_dt:
                dialog.title = ft.Text("エラー")
                dialog.content = ft.Text("終了日時が開始日時以降にされていません。")
                dialog.actions = [
                    ft.TextButton("閉じる", on_click=lambda e: page.close(dialog)),
                ]
                page.open(dialog)
                return
        
        search_params = {
            "card_name": search_cardname,
            "method": search_method,
            "eventtype": search_eventtype,
            "start_dt": start_dt,
            "end_dt": end_dt,
        }
        search_mode = True
        current_page = 0

        # ③ 件数取得→総ページ
        cnt = db.count_filtered_logs(search_cardname, search_method,search_eventtype, start_dt, end_dt)
        calc_total_pages(cnt)

        # ④ テーブルロード
        load_table(current_page)
        
    def show_all_logs(e):
        nonlocal current_page, search_mode
        search_mode = False
        current_page = 0
        calc_total_pages(db.count_all_logs())
        load_table(current_page)
        
    def open_datepicker(picker: ft.DatePicker):
        page.dialog = picker
        picker.open = True
        page.update()

    def open_timepicker(picker: ft.TimePicker):
        page.dialog = picker
        picker.open = True
        page.update()
    
    def reset(e):
        searchcardname.value = ""
        searchmethod.value = None
        searcheventtype.value = None
        start_text.value = ""
        end_text.value = ""
        start_date.value = None
        end_date.value = None
        start_time.value = time(0,0)
        end_time.value = time(23,59)
        page.update()
        
    def update_start_textbox():
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
    
    start_date.on_change = change_start_date
    end_date.on_change = change_end_date

    page_label = ft.Text("")  # 後で更新
    prev_btn = ft.ElevatedButton("⬅ 前へ",   on_click=lambda e: prev_page(e))
    next_btn = ft.ElevatedButton("次へ ➡",   on_click=lambda e: next_page(e))
    pagination_controls = ft.Row([prev_btn, page_label, next_btn], alignment=ft.MainAxisAlignment.CENTER)
    
    # ボタン定義
    search_btn = ft.ElevatedButton(
        text="検索",
        on_click=search_logs,
        width=80,
        height=40,
        bgcolor=ft.Colors.GREY_50,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(
                radius=0),
            padding=ft.padding.all(0)
        ),
    )
    show_all_btn = ft.ElevatedButton(
        text="全件表示",
        on_click=show_all_logs,
        width=80,
        height=40,
        bgcolor=ft.Colors.GREY_50,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(
                radius=0),
            padding=ft.padding.all(0)
        ),
    )
    startdate_btn = ft.ElevatedButton(text = "開始日時を選択", on_click=lambda e: open_datepicker(start_date))
    enddate_btn = ft.ElevatedButton(text = "終了日時を選択", on_click=lambda e: open_datepicker(end_date))
    reset_btn = ft.ElevatedButton(
        text="クリア",
        on_click=reset,
        width=80,
        height=40,
        bgcolor=ft.Colors.GREY_50,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(
                radius=0),
            padding=ft.padding.all(0)
        ),
    )
    back_btn = ft.TextButton("🔙", on_click=lambda e: page.go("/index"),
                    style=ft.ButtonStyle(
                        padding=ft.padding.symmetric(horizontal=20, vertical=10),
                        text_style=ft.TextStyle(size=30),
                        shape=ft.RoundedRectangleBorder(radius=10),overlay_color=ft.Colors.BLUE_100,
                    ),
                )
    # テーブル定義  
    table = ft.DataTable(
        columns=[
                    # ft.DataColumn(ft.Text("ログID", weight="bold", size=14)),
                    ft.DataColumn(ft.Text("カード名", weight="bold", size=14)),
                    ft.DataColumn(ft.Text("認証方式", weight="bold", size=14)),
                    ft.DataColumn(ft.Text("入退室の日時", weight="bold", size=14)),
                    ft.DataColumn(ft.Text("区分", weight="bold", size=14)),
        ],
        rows=[]
    )
     
    # テーブルの行をロードする関数
    def load_table(page_num: int):

        table.rows.clear()
        offset = page_num * ITEMS_PER_PAGE
        if search_mode:
            # 検索モード
            logs = db.find_log(
                search_params["card_name"], search_params["method"], search_params["eventtype"],
                search_params["start_dt"], search_params["end_dt"],
                ITEMS_PER_PAGE, offset
            )
        else:
            logs = db.find_log_by_page(ITEMS_PER_PAGE, offset)

        for _id, card_name, method, timestamp, eventtype in logs:
            event_str = "入室" if eventtype == 0 else "退室"
            table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(card_name, width=360)),
                    ft.DataCell(ft.Text(method, width=80)),
                    ft.DataCell(ft.Text(timestamp, width=140)),
                    ft.DataCell(ft.Text(event_str, width=80)),
                ])
            )
        page_label.value = f"{current_page+1} / {total_pages} ページ"
        prev_btn.disabled = current_page == 0
        next_btn.disabled = (current_page+1) >= total_pages
        page.update()
        
    if not search_mode:
        calc_total_pages(db.count_all_logs())
        
    load_table(current_page)
    scroll_table = ft.Column(
    controls=[table],
    scroll=ft.ScrollMode.ALWAYS,
    expand=True
    )
    def calc_total_pages(count: int):
        nonlocal total_pages
        total_pages = max(1, (count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    def next_page(e):
        nonlocal current_page
        if (current_page + 1) < total_pages:
            current_page += 1
            load_table(current_page)

    def prev_page(e):
        nonlocal current_page
        if current_page > 0:
            current_page -= 1
            load_table(current_page)
    
    dialog = ft.AlertDialog(
        modal=True,
    )
    # 日付と時刻の入力フィールド
    page.overlay.append(start_date)
    page.overlay.append(end_date)
    page.overlay.append(start_time)
    page.overlay.append(end_time)
    
     # 検索エリアの Column（非表示で初期化）
    search_area = ft.Container(
        content=ft.Column(
            [
                ft.Row([searchcardname, searchmethod,
                        ft.Container(searcheventtype, margin=ft.margin.only(right=30)),show_all_btn
                ]),
                ft.Row([startdate_btn,
                        ft.Container(start_text, margin=ft.margin.only(right=98)),reset_btn
                ]),
                ft.Row([enddate_btn,
                        ft.Container(end_text, margin=ft.margin.only(right=98)),search_btn
                ])
            ],
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.START
        ),
        padding=30,
        bgcolor=ft.Colors.GREY_200,
        border_radius=12,
        width=600,
        visible=False
    )

    # トグルボタンで表示/非表示切り替え
    def toggle_search_area(e):
        search_area.visible = not search_area.visible
        toggle_btn.text = "検索オプションを閉じる" if search_area.visible else "🔍 検索オプションを開く"
        page.update()

    toggle_btn = ft.ElevatedButton("🔍 検索オプションを表示", on_click=toggle_search_area)
   
    return ft.View(
        "/accesslogs",
         controls=[
            ft.Text("入/退室ログ閲覧画面",size=30, weight=ft.FontWeight.BOLD),
            toggle_btn,
            search_area,
            ft.Container(height=30),
            scroll_table,
            pagination_controls,
            back_btn,
        ],
          padding=ft.Padding(left=70, top=20, right=0, bottom=20)
    )
