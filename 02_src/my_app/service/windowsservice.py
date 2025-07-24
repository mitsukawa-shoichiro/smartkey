# Windowsサービスのエントリーポイント
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



sys.path.append(os.path.dirname(__file__))

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
        t1.start(); t2.start()
        self.threads = [t1, t2]

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