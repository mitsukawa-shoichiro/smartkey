import flet as ft
import app.views.login as login
import app.views.index as index
import app.views.card as card
import app.views.accesslogs as accesslogs
import app.views.register as register

import app.views.face_register as face_register
import app.views.face_recognition as face_recognition

import app.views.camera_regist as camera_register

import threading
from app.utils.thread_state import thread_handle, stop_event
import logging



def route(page: ft.Page):
    def page_route_change(e):
        page.title = "ドア開閉システム"
        page.views.clear()
        logging.info("%sに遷移しました", page.route)
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
            thread_handle.daemon = True
            thread_handle.start()
        elif page.route == "/register/input":
            page.views.append(register.register_input(page))
        

        elif page.route == "/face_register":
            page.views.append(face_register.face_register_view(page))
        elif page.route == "/face_register/input":
            page.views.append(face_register.face_register_register(page))
        elif page.route == "/face_recognition":
            page.views.append(face_recognition.faceView(page))


        elif page.route == "/camera_register":
            page.views.append(camera_register.camera_regist_view(page))
        
        page.update()
    page.on_route_change = page_route_change
