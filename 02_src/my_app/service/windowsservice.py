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
LOGS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)
import logs.log_config_service
# endregion

# server_dir = os.path.dirname(os.path.abspath(__file__))
# card_reader_path = os.path.join(server_dir, "nfcutils", "card_check.py")
# backsys_path = os.path.join(server_dir, "sendmail", "BackSystem.py")
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..',  'config', 'backend', 'shutdown.json'))
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    shutdown_time = json.load(f)[0]["shutdown_time"]
    shutdown_bool = json.load(f)[0]["auto_shutdown"]

# def reboot_computer():
#     now = datetime.datetime.now()
#     time.sleep(shutdown_time)
#     logging.info("ReStartComputer,Waitting"+ str(shutdown_time) + "seconds")
#     os.system("shutdown /r /t 0")  # Windows
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


from backsys import BackSystem 
from nfcutils import card_check
def run_back():
    logging.info("BackSystem thread started")
    BackSystem.main()

def run_card():
    logging.info("CardCheck thread started")
    card_check.main()

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
        if shutdown_bool:
            t3 = threading.Thread(target=reboot_computer_at_time, daemon=True)
            t3.start()
        t1.start(); t2.start()
        self.threads = [t1, t2, t3]

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
        win32event.SetEvent(self.hWaitStop)

if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(SmartKeyService)