"""
接続方式(wifi / bluetooth)を振り分ける層。

「いつ送るか」は lock_control が、「どう叩くか」は各通信モジュールが担当し、
ここは「どの経路で送るか」の判断だけを持つ。
"""
import asyncio
import logging


from my_app.service.utils.sesame import open_sesame, lock_sesame
from my_app.service.utils.sesame_bluetooth import open_sesame_bt
from my_app.config.config_loader import load_backend_config, get_value

logger = logging.getLogger(__name__)

sesame_cfg = load_backend_config("sesame_config.json")
method_cfg = get_value(sesame_cfg, "method", {}, expected_type=dict)
connect_cfg = get_value(method_cfg, "sesame_connect", "wifi", valid_values=("wifi", "bluetooth"))

def unlock_by_config(user_id: int) -> bool:
    """
    接続方式に応じて解錠する。

    Args:
        user_id (int): ユーザーID(ログ・履歴用)

    Returns:
        bool: 成功 -> True / 失敗・不明な方式 -> False
    """
    if connect_cfg == "wifi":
        success = open_sesame(user_id)
    elif connect_cfg == "bluetooth":
        success = asyncio.run(open_sesame_bt(user_id))
    else:
        logger.error("不明な接続方式です: %s", connect_cfg)
        return False

    if success:
        logger.info("%sでの解錠完了", connect_cfg)
    else:
        logger.error("%sでの解錠失敗", connect_cfg)
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
        if connect_cfg == "wifi":
            return bool(lock_sesame(user_id))
        elif connect_cfg == "bluetooth":
            logger.warning("Bluetoothでの施錠は未実装です")
            return False
        else:
            logger.error("不明な接続方式です: %s", connect_cfg)
            return False
    except Exception:
        logger.exception("施錠に失敗しました user_id=%s", user_id)
        return False