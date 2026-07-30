# my_app/config/reader_config.py
"""
カードリーダー設定の正規化と一元管理。
serialは必ずここ経由で参照すること(int/str表記ゆれを吸収済み)。
"""
import logging
from my_app.config.config_loader import load_frontend_config, get_value

logger = logging.getLogger(__name__)


def norm_serial(v):
    """serialのint/str表記ゆれを吸収する"""
    return None if v is None else str(v).strip()


_cfg = load_frontend_config("usb_settings.json")

READER_COUNT = get_value(_cfg, "設置台数", 1, int)
_devices_raw = get_value(_cfg, "devices", {}, dict)

# {方向: {"serial":正規化済, "vid":.., "pid":.., "reader_name":..}}
# JSONの記載順を維持する(入口→出口の並びがそのまま戻り値の順序になる)
DEVICES = {}
for _direction, _info in _devices_raw.items():
    if not isinstance(_info, dict):
        logger.error("devices['%s'] の形式が不正です: %r", _direction, _info)
        continue
    DEVICES[_direction] = {
        "serial": norm_serial(_info.get("serial")),
        "vid": str(_info.get("vid", "")),
        "pid": str(_info.get("pid", "")),
        "reader_name": _info.get("reader_name"),   # 未設定ならNone
    }

EXIT_SERIAL = (DEVICES.get("出口") or DEVICES.get("テスト") or {}).get("serial")
ENTRY_SERIAL = (DEVICES.get("入口") or {}).get("serial")

# 登録モードでIDmを受け付けるリーダー
REGISTER_SERIAL = EXIT_SERIAL or ENTRY_SERIAL

if REGISTER_SERIAL is None:
    logger.error("カードリーダーのserial設定が読み込めません: %r", _devices_raw)
if EXIT_SERIAL is not None and EXIT_SERIAL == ENTRY_SERIAL:
    logger.error("出口と入口のserialが同一です: %r", EXIT_SERIAL)
if len(DEVICES) != READER_COUNT:
    logger.warning("設置台数(%s)とdevices数(%s)が不一致です", READER_COUNT, len(DEVICES))