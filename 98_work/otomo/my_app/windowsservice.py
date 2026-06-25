# Windowsサービスのエントリーポイント
import json
import logging
import subprocess
import os
import time
import sys
import logging
import win32serviceutil
import win32service
import win32event
import servicemanager
import threading
import datetime
# region logs
# logs ディレクトリのパスを sys.path に追加
# LOGS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__)))
# if LOGS_PATH not in sys.path:
#     sys.path.insert(0, LOGS_PATH)
import logs.log_config_service
import logging
# endregion

# server_dir = os.path.dirname(os.path.abspath(__file__))
# card_reader_path = os.path.join(server_dir, "nfcutils", "card_check.py")
# backsys_path = os.path.join(server_dir, "sendmail", "BackSystem.py")
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),   'config', 'backend', 'shutdown.json'))
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)
    shutdown_time = data["shutdown_time"]
    shutdown_bool = bool(data["auto_shutdown"])

def reboot_computer_at_time():
    try:
        reboot_hour, reboot_minute = map(int, shutdown_time.split(':'))
    except ValueError:
        logging.error(f"時間情報が無効です: {shutdown_time}. HH:MM形式で指定してください。")
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

        logging.info("パソコン再起動します")
        os.system("shutdown /r /t 0")

from service.backsystem import BackSystem
from camera.CameraModule import CameraWorker





class SmartKeyService(win32serviceutil.ServiceFramework):
    _svc_name_        = "SmartKeyService"
    _svc_display_name_ = "Smart Key Python Service"
    _svc_description_  = "NFCリーダー監視とバックシステムを常駐実行するサービス"

    backsys_instance: BackSystem = None
    camera_worker_instance: CameraWorker = None

    def __init__(self, args):
        super().__init__(args)
        # 停止シグナル用イベント
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.stop_event = threading.Event()
        self.worker_threads = []
        self.backsys_instance = None
        self.camera_worker_instance = None

    def _run_backsystem(self):
        self.backsys_instance =BackSystem()

    def _run_camera_worker(self):
        self.camera_worker_instance = CameraWorker()
        self.camera_worker_instance.back_end_system()

    # サービス開始
    def SvcDoRun(self):
        servicemanager.LogInfoMsg("SmartKeyService started")
        # スレッド起動
        t1 = threading.Thread(target=self._run_backsystem, name="BackSystemThread", daemon=True)
        t2 = threading.Thread(target=self._run_camera_worker, name="CameraWorkerThread", daemon=True)
        t1.start()
        t2.start()
        self.worker_threads.extend([t1, t2])

        # 停止要求を待機
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

        # ここに来たら停止シグナル受信
        servicemanager.LogInfoMsg("Stopping worker threads…")
        # （BackSystem / card_check 側で while ループを回している場合は、
        #   threading.Event などを使って終了フラグを渡す実装にする）

        servicemanager.LogInfoMsg("SmartKeyService stopped")

    # サービス停止
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        
        self.backsys_instance.stop()

        self.camera_worker_instance.stop()
        
        win32event.SetEvent(self.hWaitStop)


def test():
    backsys_instance =BackSystem()
    camera_worker_instance = CameraWorker()
    camera_worker_instance.back_end_system()

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(SmartKeyService)

