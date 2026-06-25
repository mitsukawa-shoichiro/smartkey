import flet as ft

def main(page: ft.Page):
    page.title = "加法器(最小页面)"
    page.padding = 10

    display = ft.Text("0")                 # 显示栏
    input_box = ft.TextField(value="0", width=120, text_align=ft.TextAlign.RIGHT)  # 输入栏

    def add_click(e):
        try:
            a = int(input_box.value or 0)
        except ValueError:
            a = 0
        try:
            b = int(display.value or 0)
        except ValueError:
            b = 0
        display.value = str(a + b)
        page.update()

    btn = ft.ElevatedButton("加到显示", on_click=add_click)  # 按钮

    camera_index_input_area = ft.TextField(
        label="Camera Index",
        hint_text="0、1、2 …",
        value="",
        width=220,
        prefix_text="",
        keyboard_type=ft.KeyboardType.NUMBER,
        autofocus=True,
    )


    page.add(ft.Column([input_box, display, btn,camera_index_input_area], alignment=ft.MainAxisAlignment.CENTER))

if __name__ == "__main__":
    ft.app(target=main)
