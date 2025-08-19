import requests
import time
from .sendmail import send_mail
import socket
import threading
import os,sys
import json
LOGS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)
import logs.log_config_service


CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'backend', 'backendsys.json'))
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_list = json.load(f)
    battery_config = config_list[0]
    battery_mail_config = config_list[1]
    sesame_mail_config = config_list[2]
    card_reader_mail_config = config_list[3]
    system_mail_config = config_list[4]
    connectSetting = config_list[5]

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'backend', 'sesami_config.json'))
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_list = json.load(f)
    sesami_config = config_list[0]


sesame_id = sesami_config["sesame_id"]
x_api_key = sesami_config["x_api_key"]

sleep_time = int(battery_config["sleep_time"])  
battery_Limit = int(battery_config["battery_limit"])  # バッテリー残量の閾値
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
                if float(battery) <= battery_Limit :
                    mailText=battery_mail_config["TEXT"]+ response.text
                    send_mail(battery_mail_config["TITLE"], mailText)
                elif not data.get('wm2State', '取得失敗'):
                    mailText=battery_mail_config["TEXT"]+ response.text
                    send_mail(sesame_mail_config["TITLE"], sesame_mail_config["TEXT"])
            except Exception as e:
                logging.error("メール送信エラー")
                print("メール送信エラー:", e)
        except Exception as e:
            logging.error("不明エラー")
            print("不明エラー", e)
        time.sleep(sleep_time)  



def check_alive():
    HOST = '127.0.0.1'
    PORT = 54321
    heartbeatsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    heartbeatsocket.bind((HOST, PORT))
    heartbeatsocket.settimeout(1)
 
    print("死活監視システム起動...")
 
    state = True
    waittimeMax = 10
    last_AliveTime = time.time()
    while True:
        try:
            data, addr = heartbeatsocket.recvfrom(100)
            last_AliveTime = time.time()
            if data.decode('utf-8') == "DEAD" and state:
                logging.error("カードリーダーが接続されていません")
                send_mail(
                    card_reader_mail_config["TITLE"], card_reader_mail_config["TEXT"])
                print('カードリーダー異常')
                last_AliveTime = time.time()
                state = False
 
            if data.decode('utf-8') == "ALIVE" and not state:
                state = True
 
        except socket.timeout:
            pass
 
        passTime = time.time() - last_AliveTime
        if passTime > waittimeMax:
            logging.error("解錠システム異常")
            send_mail(system_mail_config["TITLE"], system_mail_config["TEXT"])
            print('システム異常')
            last_AliveTime = time.time()

 
    print('システム中止')
    heartbeatsocket.close()

def main():
    print("⏱️ sesameのバッテリーとサーバー状態を確認中...")
    threading.Thread(target=check_sesame_battery).start()
    threading.Thread(target=check_alive).start()

if __name__ == "__main__":
    main()


