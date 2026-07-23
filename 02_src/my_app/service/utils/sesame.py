"""
SESAMEとの通信を行うモジュール、
責務はSESAMEとの通信、SESAME側configの情報読み取りまでとしています。

"""
import random
import datetime
import base64
import requests
import json
import db.repository as repo
from Crypto.Hash import CMAC
from Crypto.Cipher import AES
import os
import logging
import asyncio
from my_app.service.utils.sesame_bluetooth import open_sesame_bt


logger = logging.getLogger(__name__)


CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(
    __file__), '..', '..', 'config', 'backend', 'sesame_config.json'))
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_list = json.load(f)
    sesame_config = config_list["device"]
    connect_config = config_list["method"]

sesame_id = sesame_config["sesame_id"]
x_api_key = sesame_config["x_api_key"]
secret_key = sesame_config["secret_key"]



def send_sesame_command(cmd, user_id):
    """
    SESAMEにコマンドを送信します。

    Args:
        cmd (int): 83 -> 開錠 , 82 -> 施錠
        user_id (int): ユーザーID

    Returns:
        bool: 成功 -> True , 失敗 -> False
    """
    try:
        # SESAMEの履歴用文字列つくる
        history = str(user_id)
        base64_history = base64.b64encode(bytes(history, 'utf-8')).decode()

        # APIキーをヘッダーにせってい
        headers = {'x-api-key': x_api_key}

        # SESAME API用の署名つくる
        ts = int(datetime.datetime.now().timestamp())
        message = ts.to_bytes(4, byteorder='little')
        message = message.hex()[2:8]

        cmac = CMAC.new(bytes.fromhex(secret_key), ciphermod=AES)
        cmac.update(bytes.fromhex(message))
        sign = cmac.hexdigest()

        # SESAME APIにコマンドおくる
        url = f'https://app.candyhouse.co/api/sesame2/{sesame_id}/cmd'
        body = {
            'cmd': cmd,
            'history': base64_history,
            'sign': sign
        }

        res = requests.post(url, json=body, headers=headers, timeout=10)
        res.raise_for_status()
        return True
        #print(res.status_code, res.text)

    except Exception as e:
        logger.exception("SESAMEコマンド送信失敗: cmd=%s, user_id=%s", cmd, user_id)
        return False

def open_sesame(user_id):
    # 83 であける
    return send_sesame_command(83, user_id)

def lock_sesame(user_id):
    # 82 で閉める
    return send_sesame_command(82, user_id)

def get_sesame_status():
    """
    SESAME本体の状態を取得する。

    Returns:
        成功時 -> dict {
        "status": "locked"/"unlocked",
        "position": int,
        "battery": int,
        "raw": 元のJson
        }
        失敗時 -> None

    """
    try:
        headers = {"x-api-key": x_api_key}
        url = f"https://app.candyhouse.co/api/sesame2/{sesame_id}"
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        return {
            "status": data.get("CHSesame2Status"),
            "position": data.get("position"),
            "battery": data.get("batteryPercentage"),
            "raw": data,
        }

    except Exception:
        logger.exception("SESAME状態取得失敗")
        return None

def is_sesame_locked():
    """施錠済み -> True / 未施錠 -> False / 取得失敗 -> None を返します。"""
    status = get_sesame_status()
    if status is None:
        return None
    return status["status"] == "locked"
