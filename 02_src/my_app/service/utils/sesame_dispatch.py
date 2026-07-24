"""
接続方式(wifi / bluetooth)を振り分ける層。

「いつ送るか」は lock_control が、「どう叩くか」は各通信モジュールが担当し、
ここは「どの経路で送るか」の判断だけを持つ。
"""
import asyncio
import logging
import json
from pathlib import Path

from my_app.service.utils.sesame import open_sesame, lock_sesame
from my_app.service.utils.sesame_bluetooth import open_sesame_bt

logger = logging.getLogger(__name__)




CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "backend" / "sesame_config.json"

def _load_connect_config() -> str:
    """接続方式を設定から読む。読めなければ wifi をデフォルトにする。"""
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        method = data.get("method", {}).get("sesame_connect")
        if method not in ("wifi", "bluetooth"):
            logger.warning("不明な接続方式 '%s'。wifiにフォールバック", method)
            return "wifi"
        return method
    except FileNotFoundError:
        logger.error("設定ファイルが見つかりません: %s。wifiにフォールバック", CONFIG_PATH)
        return "wifi"
    except (json.JSONDecodeError, OSError):
        logger.exception("設定ファイルの読み込みに失敗。wifiにフォールバック")
        return "wifi"


connect_config = _load_connect_config()

def unlock_by_config(user_id: int) -> bool:
    """
    接続方式に応じて解錠する。

    Args:
        user_id (int): ユーザーID(ログ・履歴用)

    Returns:
        bool: 成功 -> True / 失敗・不明な方式 -> False
    """
    if connect_config == "wifi":
        success = open_sesame(user_id)
    elif connect_config == "bluetooth":
        success = asyncio.run(open_sesame_bt(user_id))
    else:
        logger.error("不明な接続方式です: %s", connect_config)
        return False

    if success:
        logger.info("%sでの解錠完了", connect_config)
    else:
        logger.error("%sでの解錠失敗", connect_config)
    return success


def lock_by_config(user_id: int) -> bool:
    """
    接続方式に応じて施錠する。

    Args:
        user_id (int): ユーザーID(ログ・履歴用)

    Returns:
        bool: 成功 -> True / 失敗・未実装・不明な方式 -> False
    """
    try:
        if connect_config == "wifi":
            return bool(lock_sesame(user_id))
        elif connect_config == "bluetooth":
            logger.warning("Bluetoothでの施錠は未実装です")
            return False
        else:
            logger.error("不明な接続方式です: %s", connect_config)
            return False
    except Exception:
        logger.exception("施錠に失敗しました user_id=%s", user_id)
        return False