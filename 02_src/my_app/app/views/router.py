import flet as ft
import app.views.login as login
import app.views.index as index
import app.views.card as card
import app.views.accesslogs as accesslogs
import app.views.register as register
import threading
from app.utils.thread_state import thread_handle, stop_event
def route(page: ft.Page):
    def page_route_change(e):
        
        page.title = "ドア開閉システム"
        page.views.clear()
        if page.route == "/":
            page.views.append(login.login(page))
        elif page.route == "/index":
            page.views.append(index.index_view(page))
        elif page.route == "/card":
            page.views.append(card.cardView(page))
        elif page.route == "/accesslogs":
            page.views.append(accesslogs.accesslogs(page))
        elif page.route == "/register":
            global stop_event, thread_handle
            stop_event.clear()
            page.views.append(register.registering(page))
            thread_handle = threading.Thread(
                target=lambda: register.run_async_delayed_transition(page))
            thread_handle.start()
        elif page.route == "/register/input":
            page.views.append(register.register_input(page))
        page.update()
    page.on_route_change = page_route_change
