# sample.py
import flet as ft
import db_manager as db

def accesslogs(page: ft.Page):
    
    table = ft.DataTable(
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
    # cards = db.findAllCard()
    # cards = findAllCard()
    # card_dict = {card[0]: card[1] for card in cards}
    
    # logs = findAllLog()
    
    # rows = []
    # for log in logs:
    #     log_id = log[0]
    #     timestamp = log[1]
    #     method = log[2]
    #     card_id = log[3]
    #     eventtype = log[4]
    
    # card_name = card_dict.get(card_id, "不明")
    
    # rows.append(
    #         ft.DataRow([
    #             ft.DataCell(ft.Text(str(log_id))),
    #             ft.DataCell(ft.Text(card_id.card_name)),
    #             ft.DataCell(ft.Text(str(timestamp))),
    #             ft.DataCell(ft.Text(method)),
    #             ft.DataCell(ft.Text(event_str)),
    #         ])
    #     )
        

    # return ft.View(
    #     "/accesslogs",  
    #     controls=[
    #         ft.Text("ログ確認画面", style="headlineMedium"),
    #         ft.DataTable(
    #             # width=1500,
    #             # bgcolor=ft.Colors.LIGHT_BLUE_50,
    #             # border=ft.border.all(2, ft.Colors.BLACK),
    #             # border_radius=10,
    #             # vertical_lines=ft.border.BorderSide(3, ft.Colors.BLACK),
    #             # horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK),
    #             # sort_column_index=0,
    #             # sort_ascending=True,
    #             # heading_row_height=100,
    #             # data_row_color={ft.ControlState.HOVERED: "0x30FF0000"},
    #             # show_checkbox_column=True,
    #             # divider_thickness=0,
    #             # column_spacing=200,
    #             columns=[
    #                 ft.DataColumn(ft.Text("ログID"), on_sort=lambda e: print(f"{e.column_index}, {e.ascending}")),
    #                 ft.DataColumn(ft.Text("カード名"), tooltip="This is a second column", on_sort=lambda e: print(f"{e.column_index}, {e.ascending}")),
    #                 ft.DataColumn(ft.Text("入室/退室の日時"), on_sort=lambda e: print(f"{e.column_index}, {e.ascending}")),
    #                 ft.DataColumn(ft.Text("認証方式"), on_sort=lambda e: print(f"{e.column_index}, {e.ascending}")),
    #                 ft.DataColumn(ft.Text(""), on_sort=lambda e: print(f"{e.column_index}, {e.ascending}")),
    #             ],
    #             rows=rows,
    #         ),
    #         ft.ElevatedButton("← 戻る", on_click=lambda e: page.go("/index")),
    #     ]
    # )