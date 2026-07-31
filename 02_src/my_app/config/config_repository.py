"""
jsonへの依存をここでせき止めるモジュール、
いずれすべての.jsonファイルをまとめてconfig.jsonに集約して読み込みもここに集約したい
TODO: このままだと呼び出し元のインポート時点でエラー落ちになってしまうのでプロセスごとの始まりで読み込んで致命的エラーは起動しないようにしたい
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parent
CONFIG_NAME = "config.json"
CONFIG_PATH = CONFIG_DIR / CONFIG_NAME


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


_MISSING = object()
_errors: list[str] = []


def _check_type(value, expected_type) -> bool:
    """
    jsonから読み取った値の型を正しいか調べる関数

    Args:
        value (なんでも): 読み取った値
        expected_type (型名): 予想される型

    Returns:
        bool: 型が正しい -> True 型が正しくない -> False
    """
    if expected_type is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type is float:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, expected_type)


def _get_value(config, key, default=_MISSING, expected_type=None,
               valid_values=None, section=""):
    """

    Args:
        config (dict): 値が入っている辞書
        key (str): 辞書のキー
        default : 初期値 (なくてもOK)
        expected_type : 予想される型 (なくてもOK)
        valid_values (辞書) : とりうる値の列挙 (なくてもOK)
        section (str) : ログに出すときどこconfigかわかるように

    Returns:
        読み取り成功時、値を返す
    """
    full = f"{section}.{key}" if section else key

    if key not in config:
        if default is _MISSING:
            _errors.append(f"必須キーがありません: {full}")
            return None
        logger.warning("設定キー '%s' がありません。デフォルト %r を使用", full, default)
        return default

    value = config[key]

    if expected_type is not None and not _check_type(value, expected_type):
        _errors.append(
            f"型が不正: {full} = {value!r} "
            f"(期待: {expected_type.__name__}, 実際: {type(value).__name__})"
        )
        return default if default is not _MISSING else None

    if valid_values is not None and value not in valid_values:
        _errors.append(f"想定外の値: {full} = {value!r} (許可: {sorted(valid_values)})")
        return default if default is not _MISSING else None

    return value


def validate() -> None:
    """ログ設定後、main の先頭で呼ぶ"""
    if _errors:
        raise RuntimeError(
            f"設定ファイル ({CONFIG_PATH}) に問題があります:\n"
            + "\n".join(f"  - {e}" for e in _errors)
        )


_config = _load(CONFIG_PATH)

# --- config ---
_sesame_cfg = _get_value(_config, "sesame", expected_type=dict)
_mail_cfg = _get_value(_config, "mail", expected_type=dict)
_liveness_cfg = _get_value(_config, "liveness", expected_type=dict)
_battery_monitor_cfg = _get_value(_liveness_cfg, "battery_monitor", expected_type=dict)
_shutdown_cfg = _get_value(_config, "shutdown", expected_type=dict)
_account_cfg = _get_value(_config, "account", expected_type=dict)


# --- sesame ---
SESAME_ID = _get_value(_sesame_cfg, "sesame_id", expected_type=str)
SESAME_API = _get_value(_sesame_cfg, "x_api_key", expected_type=str)
MAC_ADDR = _get_value(_sesame_cfg, "mac_addr", expected_type=str)
SESAME_MAX_RETRY_COUNT = _get_value(_sesame_cfg, "max_retry_count", expected_type=int)

# --- mail ---
MAIL_ADDR = _get_value(_mail_cfg, "mail_address", expected_type=str)
MAIL_PASSWORD = _get_value(_mail_cfg, "password", expected_type=str)
MAIL_TO = _get_value(_mail_cfg, "mail_to", expected_type=str)
MAIL_SERVER = _get_value(_mail_cfg, "smtp_server", expected_type=str)
MAIL_PORT = _get_value(_mail_cfg, "port", expected_type=str)

# --- liveness ---
_battery_monitor_cfg = _get_value(_liveness_cfg, "battery_monitor", {}, expected_type=dict)

BATTERY_LIMIT = _get_value(_battery_monitor_cfg, "battery_limit", 50, expected_type=int)
BATTERY_SLEEP_TIME = _get_value(_battery_monitor_cfg, "sleep_time", 3600, expected_type=int)


def _mail_template(key: str, default_title: str = "", default_text: str = "") -> tuple[str, str]:
    """liveness配下のメール文面セクションを (TITLE, TEXT) で返す"""
    sec = _get_value(_liveness_cfg, key, {}, expected_type=dict)
    return (
        _get_value(sec, "TITLE", default_title, expected_type=str),
        _get_value(sec, "TEXT", default_text, expected_type=str),
    )


BATTERY_MAIL_TITLE, BATTERY_MAIL_TEXT = _mail_template("battery_mail")
SESAME_MAIL_TITLE, SESAME_MAIL_TEXT = _mail_template("sesame_mail")
OPEN_SENSOR_MAIL_TITLE, OPEN_SENSOR_MAIL_TEXT = _mail_template("open_sensor_mail")
CARDREADER_MAIL_TITLE, CARDREADER_MAIL_TEXT = _mail_template("cardreader_mail")
SYSTEM_MAIL_TITLE, SYSTEM_MAIL_TEXT = _mail_template("system_mail")

# --- shutdown ---
AUTO_SHUTDOWN = _get_value(_shutdown_cfg, "auto_shutdown", False, expected_type=bool)
SHUTDOWN_TIME = _get_value(_shutdown_cfg, "shutdown_time", "09:00", expected_type=str)

# --- account ---
USER_NAME = _get_value(_account_cfg, "admin", expected_type=str)
PASSWORD = _get_value(_account_cfg, "password", expected_type=str)
