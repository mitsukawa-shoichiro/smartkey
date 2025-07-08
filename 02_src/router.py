import flet as ft
import login
import index
import card
import accesslogs

def route(page: ft.Page):
    
    def page_route_change(e):
        page.title = "ドア開閉システム"
        page.views.clear()
        if page.route == "/":
            page.views[login.login(page)]
        elif page.route == "/index":
            page.views[index.index_view(page)]
        elif page.route == "/card":
            page.views.append(card.cardView(page))
        elif page.route == "/accesslogs":
            page.views.append(accesslogs.accesslogs(page))
        page.update()
    page.on_route_change = page_route_change