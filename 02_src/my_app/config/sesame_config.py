"""
SESAME関連設定の一元管理。
接続方式・デバイス情報は必ずここ経由で参照すること。
"""
import logging
from my_app.config.config_loader import load_backend_config, get_value

logger = logging.getLogger(__name__)

_cfg = load_backend_config("sesame_config.json")
_method = get_value(_cfg, "method", {}, expected_type=dict)
_device = get_value(_cfg, "device", {}, expected_type=dict)

CONNECT_METHOD = get_value(
    _method, "sesame_connect", "wifi", valid_values=("wifi", "bluetooth"))

SESAME_ID = get_value(_device, "sesame_id", None, expected_type=str)
X_API_KEY = get_value(_device, "x_api_key", None, expected_type=str)
SECRET_KEY = get_value(_device, "secret_key", None, expected_type=str)

if not all([SESAME_ID, X_API_KEY, SECRET_KEY]):
    logger.error("SESAMEの認証情報が不足しています(解錠できません)")