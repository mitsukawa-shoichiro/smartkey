import logging
import logs.log_config_service
import requests
import time
from .sendmail import send_mail
import socket
import threading
import os
import sys
import json
import asyncio
from utils.sesami_bluetooth import SsmBleClient

LOGS_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..'))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)


CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(
    __file__), '..', '..', 'config', 'backend', 'backendsys.json'))
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_list = json.load(f)
    battery_config = config_list["battery_observation"]
    battery_mail_config = config_list["battery_mail"]
    sesame_mail_config = config_list["sesame_mail"]
    card_reader_mail_config = config_list["cardreader_mail"]
    system_mail_config = config_list["system_mail"]

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(
    __file__), '..', '..', 'config', 'backend', 'sesami_config.json'))
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_list = json.load(f)
    sesami_config = config_list["device"]
    connection_method = config_list["method"]["sesami_connect"]


sesame_id = sesami_config["sesame_id"]
x_api_key = sesami_config["x_api_key"]

sleep_time = int(battery_config["sleep_time"])
battery_Limit = int(battery_config["battery_limit"])  # バッテリー残量の閾値

def run_sesame_monitor():
    if connection_method == "wifi":
        logging.info("WiFi経由でセサミ監視開始")
        check_sesame_battery()
    else:
        logging.info("Bluetooth経由でセサミ監視開始")
        # asyncio.run(check_sesame_battery_bt())
        
def check_sesame_battery():
    '''
    # sesameのバッテリー残量を確認し、50%以下ならメールを送信する

    '''
    battery_state = True
    sesame_state = True
    while (1):
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
                if float(battery) <= battery_Limit:
                    logging.error(f"バッテリーが{battery_Limit}%以下になりました。")
                    if battery_state:
                        mailText = battery_mail_config["TEXT"] + response.text
                        send_mail(battery_mail_config["TITLE"], mailText)
                        battery_state = False

                elif not battery_state:
                    logging.info(f"バッテリーが{battery_Limit}%以上に戻りました。")
                    battery_state = True

                if not data.get('wm2State', '取得失敗'):
                    logging.error("セサミと接続できません")
                    if sesame_state:
                        mailText = battery_mail_config["TEXT"] + response.text
                        send_mail(
                            sesame_mail_config["TITLE"], sesame_mail_config["TEXT"])
                        sesame_state = False
                elif not sesame_state:
                    logging.info("セサミとの接続が回復しました")
                    sesame_state = True

            except Exception as e:
                logging.error("メール送信エラー")
                print("メール送信エラー:", e)
        except Exception as e:
            logging.error("不明エラー")
            print("不明エラー", e)
        time.sleep(sleep_time)

# async def check_sesame_battery_bt():
#     '''
#     # Bluetooth経由でセサミのバッテリー残量を確認し、50%以下ならメールを送信する
#     '''
#     battery_state = True
#     while (1):
#         try:
#             sbc = SsmBleClient.get_instance()
#             await sbc.connect()
#             await sbc.start_notify()
#             await sbc.login()
#             if sbc.isLogin:
#                 battery = sbc.battery
#                 logging.info(f"Bluetoothバッテリー残量: {battery}%")
#                 try:
#                     if float(battery) <= battery_Limit:
#                         logging.error(f"バッテリーが{battery_Limit}%以下になりました。")
#                         if battery_state:
#                             mailText = battery_mail_config["TEXT"] + f" バッテリー残量: {battery}%"
#                             send_mail(battery_mail_config["TITLE"], mailText)
#                             battery_state = False

#                     elif not battery_state:
#                         logging.info(f"バッテリーが{battery_Limit}%以上に戻りました。")
#                         battery_state = True
#                 except Exception as e:
#                     logging.error("メール送信エラー")
#                     print("メール送信エラー:", e)
                    
#             await sbc.stop_notify()
#             await sbc.disconnect()
#         except Exception as e:
#             logging.error(f"Bluetooth接続失敗: {e}")
#         await asyncio.sleep(sleep_time)

def check_alive():
    HOST = '127.0.0.1'
    PORT = 54321
    heartbeatsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    heartbeatsocket.bind((HOST, PORT))
    heartbeatsocket.settimeout(1)

    print("死活監視システム起動...")

    card_reader_state = True
    system_state = True
    waittimeMax = 10
    last_AliveTime = time.time()
    while True:
        try:
            data, addr = heartbeatsocket.recvfrom(100)
            last_AliveTime = time.time()
            if data.decode('utf-8') == "DEAD" and card_reader_state:

                logging.error("カードリーダーが指定台数分接続されていません")
                send_mail(
                    card_reader_mail_config["TITLE"], card_reader_mail_config["TEXT"])
                print('カードリーダー異常')
                last_AliveTime = time.time()
                card_reader_state = False

            if data.decode('utf-8') == "ALIVE" and not card_reader_state:
                logging.info("カードリーダが指定台数接続されました")
                card_reader_state = True

        except socket.timeout:
            pass

        passTime = time.time() - last_AliveTime
        if passTime > waittimeMax:
            logging.error("解錠システム異常")
            if system_state:

                send_mail(system_mail_config["TITLE"],
                          system_mail_config["TEXT"])
                print('システム異常')
                last_AliveTime = time.time()
                system_state = False

        elif not system_state:
            system_state = True
            logging.info("システム正常に戻りました")


def main():
    print("⏱️ sesameのバッテリーとサーバー状態を確認中...")
    threading.Thread(target=run_sesame_monitor).start()
    threading.Thread(target=check_alive).start()


if __name__ == "__main__":
    main()
