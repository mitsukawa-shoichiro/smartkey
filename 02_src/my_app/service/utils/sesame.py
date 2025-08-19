import random
import datetime
import base64
import requests
import json
from Crypto.Hash import CMAC
from Crypto.Cipher import AES
import os

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(
    __file__), '..', '..', 'config', 'backend', 'sesami_config.json'))
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_list = json.load(f)
    sesami_config = config_list[0]

sesame_id = sesami_config["sesame_id"]
x_api_key = sesami_config["x_api_key"]
secret_key = sesami_config["secret_key"]


def open_sesame():
    try:
        cmd = 83  # 88/82/83 = toggle/lock/unlock
        history = str(random.random())
        base64_history = base64.b64encode(bytes(history, 'utf-8')).decode()

        print(base64_history)
        headers = {'x-api-key': x_api_key}
        cmac = CMAC.new(bytes.fromhex(secret_key), ciphermod=AES)

        ts = int(datetime.datetime.now().timestamp())
        message = ts.to_bytes(4, byteorder='little')
        message = message.hex()[2:8]
        print("message:" + message)
        cmac = CMAC.new(bytes.fromhex(secret_key), ciphermod=AES)

        cmac.update(bytes.fromhex(message))
        sign = cmac.hexdigest()
        # 鍵の操作
        url = f'https://app.candyhouse.co/api/sesame2/{sesame_id}/cmd'
        body = {
            'cmd': cmd,
            'history': base64_history,
            'sign': sign
        }
        res = requests.post(url, json.dumps(body), headers=headers)
        print(res.status_code, res.text)
    except Exception as e:
        print("エラー:" + e)


if __name__ == "__main__":
    open_sesame()
