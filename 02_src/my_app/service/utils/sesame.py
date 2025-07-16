import datetime, base64, requests, json
from Crypto.Hash import CMAC
from Crypto.Cipher import AES

def open_sesame():
    try:
        uuid = "11200413-0002-0611-3F00-9200FFFFFFFF"
        secret_key = 'daf80ccf3864885736250cd73849354c'
        api_key = "O3R8DiaBCR2CD8mi10ibR9yT5OMqZHByaDmSCmnT"

        cmd = 88  # 88/82/83 = toggle/lock/unlock
        history = 'test2'
        base64_history = base64.b64encode(bytes(history, 'utf-8')).decode()

        print(base64_history)
        headers = {'x-api-key': api_key}
        cmac = CMAC.new(bytes.fromhex(secret_key), ciphermod=AES)

        ts = int(datetime.datetime.now().timestamp())
        message = ts.to_bytes(4, byteorder='little')
        message = message.hex()[2:8]
        print("message:" + message)
        cmac = CMAC.new(bytes.fromhex(secret_key), ciphermod=AES)

        cmac.update(bytes.fromhex(message))
        sign = cmac.hexdigest()
        # 鍵の操作
        url = f'https://app.candyhouse.co/api/sesame2/{uuid}/cmd'
        body = {
            'cmd': cmd,
            'history': base64_history,
            'sign': sign
        }
        res = requests.post(url, json.dumps(body), headers=headers)
        print(res.status_code, res.text)
    except Exception as e:
        print("エラー:" + e)