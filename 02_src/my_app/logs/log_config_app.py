"""
log_config.py
グローバルロギング初期化モジュール：プロジェクトのどこでも `import log_config` で利用可能。
"""
import os
import json
import logging.config

# 設定ファイルのパス
BASE_DIR = os.path.dirname(__file__) + "\\..\\config"
config_path = os.path.join(BASE_DIR, "app_log_config.json")

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

logging.config.dictConfig(config)

# テストログ
logger = logging.getLogger(__name__)
logger.debug("デバッグメッセージ")
logger.info("情報メッセージ")
