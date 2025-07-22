import requests
import time
from sendmail import send_mail
import socket
import threading
import os,sys
LOGS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)
import logs.log_config_service

sesame_id = "11200413-0002-0611-3F00-9200FFFFFFFF"
x_api_key = "O3R8DiaBCR2CD8mi10ibR9yT5OMqZHByaDmSCmnT"

sleep_time = 3600
import logging
def check_sesame_battery():
    '''
    # sesameのバッテリー残量を確認し、50%以下ならメールを送信する
    '''
    while(1):
        try:
            sesame_url = f"https://app.candyhouse.co/api/sesame2/{sesame_id}"
            headers = {"x-api-key": x_api_key}
            response = requests.get(sesame_url, headers=headers)
            print(response.text)
            try:
                data = response.json()
                battery = data.get('batteryPercentage', '取得失敗')
            except Exception as e:
                battery = f"JSON解析失敗: {e}"
            print("バッテリー残量:", battery)
            logging.info(f"バッテリー残量: {battery}")
            print("wm2State:", data.get('wm2State', '取得失敗'))

            try:
                if float(battery) <= 50 or not data.get('wm2State', '取得失敗'):
                    mail_body = f"sesami状態は:\n{response.text}\n\n電池残量:\n{battery}"
                    send_mail('セサミ状態通知', mail_body)
                    print('メール送信完了')
            except Exception as e:
                logging.error("バッテリー値の変換またはメール送信中にエラー")
                print("バッテリー値の変換またはメール送信中にエラー:", e)
        except Exception as e:
            logging.error("バッテリー値の変換またはメール送信中にエラー")
            print("バッテリー確認中またはメール送信中にエラー:", e)
        time.sleep(sleep_time)  



def check_alive():
    HOST = '127.0.0.1'
    PORT = 12345
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    sock.settimeout(1)  # 每1秒检查一次

    print("死活監視システム起動...")

    waittimeMax = 5  # 超时时间（秒）
    last_AliveTime = time.time()
    while True:
        try:
            data, addr = sock.recvfrom(100)
            last_AliveTime = time.time()
        except socket.timeout:
            pass  # 没收到包，继续检查超时

        passTime = time.time() - last_AliveTime
        if passTime > waittimeMax:
            logging.error("開錠システム異常")
            mail_body = "開錠システムが動作していない"
            send_mail('システム異常', mail_body)
            print('システム異常')
            last_AliveTime = time.time()  # 避免重复报警
            break
    print('システム中止')
    sock.close()



if __name__ == "__main__":
    print("⏱️ sesameのバッテリーとサーバー状態を確認中...")
    threading.Thread(target=check_sesame_battery).start()
    threading.Thread(target=check_alive).start()


