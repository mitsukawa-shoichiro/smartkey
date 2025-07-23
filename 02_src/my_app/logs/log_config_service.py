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
config_path = os.path.join(BASE_DIR, "service_log_config.json")

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

logging.config.dictConfig(config)

# ---- グローバル例外フック ----
root = logging.getLogger()


def _excepthook(exc_type, exc, tb):
    if issubclass(exc_type, KeyboardInterrupt):
        return sys.__excepthook__(exc_type, exc, tb)
    root.critical("UNCAUGHT EXCEPTION", exc_info=(exc_type, exc, tb))


sys.excepthook = _excepthook
