"""
log_config.py
グローバルロギング初期化モジュール：プロジェクトのどこでも `import log_config` で利用可能。
"""
import logging
import logging.handlers
import os, sys, queue

# ---- ログパスとファイル ----
LOG_DIR = os.path.join(os.path.dirname(__file__))
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "app.log")

# ---- フォーマッター ----
FMT = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"
formatter = logging.Formatter(FMT, datefmt="%Y-%m-%d %H:%M:%S")

# ---- ファイルハンドラー（日次ローテーション）----
file_hdl = logging.handlers.TimedRotatingFileHandler(
    LOG_PATH, when="midnight", backupCount=10, encoding="utf-8"
)
file_hdl.setFormatter(formatter)
file_hdl.setLevel(logging.INFO)        

# ---- コンソールハンドラー ----
console_hdl = logging.StreamHandler(sys.stdout)
console_hdl.setFormatter(formatter)
console_hdl.setLevel(logging.DEBUG)      

# # ---- ルートロガーの設定 ----
root = logging.getLogger()
root.setLevel(logging.INFO)
root.addHandler(file_hdl)
root.addHandler(console_hdl)


# ---- グローバル例外フック ----
def _excepthook(exc_type, exc, tb):
    if issubclass(exc_type, KeyboardInterrupt):
        return sys.__excepthook__(exc_type, exc, tb)
    root.critical("UNCAUGHT EXCEPTION", exc_info=(exc_type, exc, tb))

sys.excepthook = _excepthook
