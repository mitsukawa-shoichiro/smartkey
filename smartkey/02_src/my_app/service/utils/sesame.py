import random
import datetime
import base64
import requests
import json
from Crypto.Hash import CMAC
from Crypto.Cipher import AES
import os
import logging
logger = logging.getLogger(__name__)


CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(
    __file__), '..', '..', 'config', 'backend', 'sesame_config.json'))
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_list = json.load(f)
    sesame_config = config_list["device"]

sesame_id = sesame_config["sesame_id"]
x_api_key = sesame_config["x_api_key"]
secret_key = sesame_config["secret_key"]



def send_sesame_command(cmd: int):
    try:
        # SESAMEの履歴用文字列つくる
        history = str(random.random())
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
        print(res.status_code, res.text)

    except Exception as e:
        logger.error("エラー:" + str(e))

def open_sesame():
    # 83 であける
    send_sesame_command(83)

def lock_sesame():
    # 82 で閉める
    send_sesame_command(82)
