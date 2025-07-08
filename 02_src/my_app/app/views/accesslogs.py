import flet as ft
import app.models.db_manager as db
from datetime import datetime


def accesslogs(page: ft.Page):
    
    page.title = "ログ閲覧画面"
    
    cardname = ft.TextField(label="カード名")
    method = ft.TextField(label="認証方式")
    startdate = ft.DatePicker(label="開始日時")
    enddate = ft.DatePicker(label="終了日時")
    eventtype = ft.dropdown(label="入室/退室の区別", options=[
        ft.dropdown.Option("選択してください", value=""),
        ft.dropdown.Option("入室", value="0"),
        ft.dropdown.Option("退室", value="1"),
    ])
    
    def search_logs(e):
        
        search_cardname = cardname.value
        search_method = method.value
        search_startdate = startdate.value
        search_enddate = enddate.value
        search_eventtype = eventtype.value

        logs = db.findLog(search_cardname, search_method, search_startdate, search_enddate, search_eventtype)

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

    search_btn = ft.ElevatedButton("検索", on_click=search_logs)

    table = ft.DataTable(
        # width=1500,
        # bgcolor=ft.Colors.LIGHT_BLUE_50,
        # border=ft.border.all(2, ft.Colors.BLACK),
        # border_radius=10,
        # vertical_lines=ft.border.BorderSide(3, ft.Colors.BLACK),
        # horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK),
        # sort_column_index=0,
        # sort_ascending=True,
        # heading_row_height=100,
        # data_row_color={ft.ControlState.HOVERED: "0x30FF0000"},
        # show_checkbox_column=True,
        # divider_thickness=0,
        # column_spacing=200,
        
        columns=[
            
            ft.DataColumn(ft.Text("ログID")),
            ft.DataColumn(ft.Text("カード名")),
            ft.DataColumn(ft.Text("認証方式")),
            ft.DataColumn(ft.Text("入室/退室の日時")),
            ft.DataColumn(ft.Text("")),
        ],
        rows=[],
    )
     
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
    return ft.View(
            "/accesslogs",
            [
                table,
                
                ft.ElevatedButton("戻る", on_click=lambda e: page.go("/index")),
                
            ],
        )
 