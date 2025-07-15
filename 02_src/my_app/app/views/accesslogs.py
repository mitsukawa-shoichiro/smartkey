from datetime import datetime
from datetime import time
import flet as ft
import app.models.db_manager as db

# ログ閲覧画面
def accesslogs(page: ft.Page):

    start_text = ft.TextField(label="開始日時", width=200, height=48)
    end_text = ft.TextField(label="終了日時", width=200, height=48)
    
    dialog = ft.AlertDialog(
        modal=True,
    )
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
        search_method = searchmethod.value.strip() if searchmethod.value else None
        search_cardname = searchcardname.value.strip() if searchcardname.value else None
        search_eventtype = int(searcheventtype.value.strip()) if searcheventtype.value else None
        start_dt = None
        end_dt = None
        
        if start_text.value != "" and end_text.value != "":
            start_dt = datetime.combine(start_date.value, start_time.value).replace(second=0)
            end_dt = datetime.combine(end_date.value, end_time.value).replace(second=59)

            if start_dt and end_dt and end_dt < start_dt:
                dialog.title = ft.Text("エラー")
                dialog.content = ft.Text("終了日時が開始日時以降にされていません。")
                dialog.actions = [
                    ft.TextButton("閉じる", on_click=lambda e: page.close(dialog)),
                ]
                page.open(dialog)
                return
        
        
        logs = db.findLog(search_cardname, search_method, search_eventtype,start_dt,end_dt)

        table.rows.clear()
        for log in logs:
            id, cardname, method,timestamp, eventtype = log
            event_str = "入室" if eventtype == 0 else "退室"
            
            table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(id))),
                        ft.DataCell(ft.Text(cardname)),
                        ft.DataCell(ft.Text(method)),
                        ft.DataCell(ft.Text(timestamp)),
                        ft.DataCell(ft.Text(event_str)),
                    ]
                )
            )

        page.update()
        
    def open_datepicker(picker: ft.DatePicker):
        page.dialog = picker
        picker.open = True
        page.update()

    def open_timepicker(picker: ft.TimePicker):
        page.dialog = picker
        picker.open = True
        page.update()
    
    def show_all_logs(e):
        load_table()
        
    def reset_dropdown(e):
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

    # ボタン定義
    search_btn = ft.ElevatedButton("検索", on_click=search_logs)
    show_all_btn = ft.ElevatedButton("全件表示", on_click=show_all_logs)
    startdate_btn = ft.ElevatedButton(text = "開始日時を選択", on_click=lambda e: open_datepicker(start_date))
    enddate_btn = ft.ElevatedButton(text = "終了日時を選択", on_click=lambda e: open_datepicker(end_date))
    reset_btn = ft.ElevatedButton("リセット", on_click=reset_dropdown)
    # テーブル定義  
    table = ft.DataTable(
        columns=[
                    ft.DataColumn(ft.Text("ログID", weight="bold", size=14)),
                    ft.DataColumn(ft.Text("カード名", weight="bold", size=14)),
                    ft.DataColumn(ft.Text("認証方式", weight="bold", size=14)),
                    ft.DataColumn(ft.Text("入退室の日時", weight="bold", size=14)),
                    ft.DataColumn(ft.Text("区分", weight="bold", size=14)),
        ],
        rows=[]
    )
     
    # テーブルの行をロードする関数
    def load_table():

        table.rows.clear()
        logs = db.findAllLog()
        for id, card_name, method, timestamp, eventtype in logs:
        
            if eventtype == 0:
                event_str = "入室"
            elif eventtype == 1:
                event_str = "退室"
            table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(id)),
                        ft.DataCell(ft.Text(card_name)),
                        ft.DataCell(ft.Text(method)),
                        ft.DataCell(ft.Text(timestamp)),
                        ft.DataCell(ft.Text(event_str)),
                    ]
                )
            )
        page.update()
        
    load_table()
    scroll_table = ft.Column(
    controls=[table],
    scroll=ft.ScrollMode.ALWAYS,
    expand=True
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
                ft.Row([searchcardname, searchmethod, searcheventtype], spacing=20),
                ft.Row([ft.Text("開始日時:", width=80), startdate_btn, start_text], spacing=10),
                ft.Row([ft.Text("終了日時:", width=80), enddate_btn, end_text], spacing=10),
                ft.Row([search_btn,show_all_btn, reset_btn], alignment=ft.MainAxisAlignment.END, spacing=20),
            ],
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.START
        ),
        padding=20,
        bgcolor=ft.Colors.GREY_100,
        border_radius=12,
        width=800,
        visible=False
    )

    # トグルボタンで表示/非表示切り替え
    def toggle_search_area(e):
        search_area.visible = not search_area.visible
        toggle_btn.text = "検索オプションを隠す" if search_area.visible else "🔍 検索オプション表示"
        page.update()

    toggle_btn = ft.ElevatedButton("🔍 検索オプションを表示", on_click=toggle_search_area)
   
    return ft.View(
        "/accesslogs",
         controls=[
            ft.Text("入/退室ログ閲覧画面", size=24, weight="bold"),
            toggle_btn,
            search_area,
            scroll_table,
            ft.ElevatedButton("戻る", on_click=lambda e: page.go("/index")),
        ]
    )
