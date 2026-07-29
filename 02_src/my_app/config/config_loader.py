# my_app/config/config_loader.py
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parent

def _load(path: Path) -> dict:
    """
    指定されたパスのconfigを読み込む、無い/壊れている場合は空dict + ログ出力
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("設定ファイルが見つかりません: %s。空の設定で継続します", path)
        return {}
    except json.JSONDecodeError:
        logger.exception("設定ファイルのJSONが壊れています: %s。空の設定で継続します", path)
        return {}


def get_value(config: dict, key: str, default, expected_type=None, valid_values=None):
    """
    configから値を取り出す。欠落・型違い・不正値を検出してログを出し、
    問題があればdefaultを返す。
    """
    if key not in config:
        logger.warning("設定キー '%s' がありません。デフォルト %r を使用", key, default)
        return default
    value = config[key]
    if expected_type is not None and not isinstance(value, expected_type):
        logger.error("設定キー '%s' の型が不正 (%r)。デフォルト %r を使用", key, value, default)
        return default
    if valid_values is not None and value not in valid_values:
        logger.warning("設定キー '%s' の値 %r は想定外。デフォルト %r を使用", key, value, default)
        return default
    return value

def load_backend_config(filename) -> dict:
    return _load(CONFIG_DIR / "backend" / filename)

def load_frontend_config(filename) -> dict:
    return _load(CONFIG_DIR / filename)