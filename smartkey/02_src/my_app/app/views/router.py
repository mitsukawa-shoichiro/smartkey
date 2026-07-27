import flet as ft
import app.views.login as login
import app.views.index as index
import app.views.card as card
import app.views.accesslogs as accesslogs
import app.views.register as register


import app.views.face_register as face_register
import app.views.face_recognition as face_recognition

import app.views.camera_register as camera_register


import threading
from app.utils.thread_state import thread_handle, stop_event
import logging
import urllib.parse

logger = logging.getLogger(__name__)

def route(page: ft.Page):
    def page_route_change(e):
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(e.route).query))
        error_message = params.get("error", "")
        page.title = "ドア開閉システム"
        page.views.clear()
        logger.info("%sに遷移しました", e.route)
        if e.route == "/":
            page.views.append(login.login(page))
        elif e.route.startswith("/index"):
            logger.info("index_viewに遷移しました。error_message=%s", error_message)
            page.views.append(index.index_view(page, error_message))
        elif e.route == "/card":
            page.views.append(card.cardView(page))
        elif e.route == "/accesslogs":
            page.views.append(accesslogs.accesslogs(page))
        elif e.route == "/register":
            logger.info("registerに遷移しました")
            global stop_event, thread_handle
            stop_event.clear()
            page.views.append(register.registering(page))
            thread_handle = threading.Thread(
                target=lambda: register.run_async_delayed_transition(page))
            thread_handle.daemon = True
            thread_handle.start()
        elif e.route == "/register/input":
            page.views.append(register.register_input(page))


        elif e.route == "/face_register":
            page.views.append(face_register.face_register_view(page))
        elif e.route == "/face_register/input":
            page.views.append(face_register.face_register_register(page))
        elif e.route == "/face_recognition":
            page.views.append(face_recognition.faceView(page))


        elif e.route == "/camera_register":
            page.views.append(camera_register.camera_register_view(page))



        page.update()
    page.on_route_change = page_route_change
