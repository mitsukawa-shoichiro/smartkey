"""
log_config.py
グローバルロギング初期化モジュール：プロジェクトのどこでも `import log_config` で利用可能。
"""
import os
import json
import logging.config
import sys


# 設定ファイルのパス
BASE_DIR = os.path.dirname(__file__) + "\\..\\config"
config_path = os.path.join(BASE_DIR, "app_log_config.json")

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
log_file_path = os.path.join(log_dir, "app.log")
print(f"Log file path: {log_file_path}")
config["handlers"]["fileHandler"]["filename"] = log_file_path

logging.config.dictConfig(config)

# ---- グローバル例外フック ----
root = logging.getLogger()


def _excepthook(exc_type, exc, tb):
    if issubclass(exc_type, KeyboardInterrupt):
        return sys.__excepthook__(exc_type, exc, tb)
    root.critical("UNCAUGHT EXCEPTION", exc_info=(exc_type, exc, tb))


sys.excepthook = _excepthook
logging.info("Log configuration loaded successfully")
