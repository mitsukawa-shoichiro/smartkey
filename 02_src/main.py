import flet as ft
import login
import index
import sample


def main(page: ft.Page):
    page.title = "ドア開閉システム"
    #login_user = {"name": None}
    def route_change(route):
        page.views.clear()
        if page.route == "/":
            page.views.append(login.login(page))
        elif page.route == "/index":
            page.views.append(index.index_view(page))
        elif page.route == "/sample":
            page.views.append(sample.sample(page))
        # elif page.route == "/logs":
        #     page.views.append(log_manage_view())
        page.update()

    page.on_route_change = route_change
    page.go(page.route)

ft.app(target=main)