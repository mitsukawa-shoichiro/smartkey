import flet as ft
import login
import index
import card
import accesslogs

def main(page: ft.Page):
    page.title = "ドア開閉システム"
    #login_user = {"name": None}
    def route_change(route):
        page.views.clear()
        if page.route == "/":
            page.views.append(login.login(page))
        elif page.route == "/index":
            page.views.append(index.index_view(page))
        elif page.route == "/card":
            page.views.append(card.cardView(page))
        elif page.route == "/accesslogs":
            page.views.append(accesslogs.accesslogs(page))
        page.update()

    page.on_route_change = route_change
    page.go(page.route)

ft.app(target=main)