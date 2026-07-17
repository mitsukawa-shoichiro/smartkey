# Windowsサービスのエントリーポイント
import json
import logging
import subprocess
import os
import time
import sys
import win32serviceutil
import win32service
import win32event
import servicemanager
import threading
import datetime
# region logs
# logs ディレクトリのパスを sys.path に追加
BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)

# pywin32のサービスは pythonservice.exe というホストで動くため、
# .venv の site-packages が sys.path に入らない(venvの有効化を知らない)。
# my_app.* は上のBASE_PATHで辿れるが、cv2/flet等の外部パッケージは
# ここで明示的にパスを通さないとimportできない。

import my_app.logs.log_config_service
logger = logging.getLogger(__name__)  # logに書き込む用
# endregion

# server_dir = os.path.dirname(os.path.abspath(__file__))
# card_reader_path = os.path.join(server_dir, "nfcutils", "card_check.py")
# backsys_path = os.path.join(server_dir, "sendmail", "back_system.py")
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..',  'config', 'backend', 'shutdown.json'))
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)
    shutdown_time = data["shutdown_time"]
    shutdown_bool = bool(data["auto_shutdown"])

# def reboot_computer():
#     now = datetime.datetime.now()
#     time.sleep(shutdown_time)
#     logger.info("ReStartComputer,Waitting"+ str(shutdown_time) + "seconds")
#     os.system("shutdown /r /t 0")  # Windows
def reboot_computer_at_time():
    try:
        reboot_hour, reboot_minute = map(int, shutdown_time.split(':'))
    except ValueError:
        logger.error(f"時間情報が無効です: {shutdown_time}. HH:MM形式で指定してください。")
        return

    while True:
        now = datetime.datetime.now()
        reboot_time_today = now.replace(hour=reboot_hour, minute=reboot_minute, second=0, microsecond=0)

        if now < reboot_time_today:
            wait_seconds = (reboot_time_today - now).total_seconds()
        else:
            reboot_time_tomorrow = reboot_time_today + datetime.timedelta(days=1)
            wait_seconds = (reboot_time_tomorrow - now).total_seconds()

        time.sleep(wait_seconds)

        logger.info("パソコン再起動します")
        os.system("shutdown /r /t 0")


from my_app.service.backsys import back_system
from my_app.daemon import reader_daemon
def run_back():
    logger.info("back_system thread started")
    back_system.main()

def run_card():
    logger.info("reader_daemon thread started")
    reader_daemon.main()

from my_app.camera.CameraModule import CameraWorker
camera_worker = None
def run_camera():
    global camera_worker

    try:
        logger.info("かめらわーかーすれっどすたーと")
        camera_worker = CameraWorker()
        camera_worker.back_end_system()
    except Exception:
        logger.exception("えらーや")

class SmartKeyService(win32serviceutil.ServiceFramework):
    _svc_name_        = "SmartKeyService"
    _svc_display_name_ = "Smart Key Python Service"
    _svc_description_  = "NFCリーダー監視とバックシステムを常駐実行するサービス"

    def __init__(self, args):
        super().__init__(args)
        # 停止シグナル用イベント
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.threads   = []

    # サービス開始
    def SvcDoRun(self):
        servicemanager.LogInfoMsg("SmartKeyService started")
        # スレッド起動
        t1 = threading.Thread(target=run_back, daemon=True)
        t2 = threading.Thread(target=run_card, daemon=True)
        t_camera = threading.Thread(target=run_camera, daemon=True)

        self.threads = [t1, t2, t_camera]

        if shutdown_bool:
            t_shutdown = threading.Thread(
                target = reboot_computer_at_time,
                daemon = True
            )
            self.threads.append(t_shutdown)

        for thread in self.threads:
            thread.start()

        # 停止要求を待機
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

        # ここに来たら停止シグナル受信
        servicemanager.LogInfoMsg("Stopping worker threads…")
        reader_daemon.stop()


        servicemanager.LogInfoMsg("SmartKeyService stopped")

    # サービス停止
    def SvcStop(self):
        global camera_worker

        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

        if camera_worker is not None:
            camera_worker.stop()

        win32event.SetEvent(self.hWaitStop)

if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(SmartKeyService)