import logging
import my_app.logs.log_config_service
import requests
import time
from .sendmail import send_mail
import socket
import threading
import os
import sys
import json
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
    __file__), '..', '..', 'config', 'backend', 'sesame_config.json'))
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_list = json.load(f)
    sesame_config = config_list["device"]


sesame_id = sesame_config["sesame_id"]
x_api_key = sesame_config["x_api_key"]

sleep_time = int(battery_config["sleep_time"])
battery_Limit = int(battery_config["battery_limit"])  # バッテリー残量の閾値

logger = logging.getLogger(__name__)  # logに書き込む用

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
            logger.debug(f"Response: {response.text}")
            try:
                data = response.json()
                battery = data.get('batteryPercentage', '取得失敗')
            except Exception as e:
                battery = f"JSON解析失敗: {e}"
            logger.debug(f"バッテリー残量: {battery}")
            logger.info(f"バッテリー残量: {battery}")
            logger.debug(f"wm2State: {data.get('wm2State', '取得失敗')}")
            try:
                if float(battery) <= battery_Limit:
                    logger.error(f"バッテリーが{battery_Limit}%以下になりました。")
                    if battery_state:
                        mailText = battery_mail_config["TEXT"] + response.text
                        send_mail(battery_mail_config["TITLE"], mailText)
                        battery_state = False

                elif not battery_state:
                    logger.info(f"バッテリーが{battery_Limit}%以上に戻りました。")
                    battery_state = True

                if not data.get('wm2State', '取得失敗'):
                    logger.error("セサミと接続できません")
                    if sesame_state:
                        mailText = battery_mail_config["TEXT"] + response.text
                        send_mail(
                            sesame_mail_config["TITLE"], sesame_mail_config["TEXT"])
                        sesame_state = False
                elif not sesame_state:
                    logger.info("セサミとの接続が回復しました")
                    sesame_state = True

            except Exception as e:
                logger.error("メール送信エラー")
                logger.debug(f"メール送信エラー: {e}")
        except Exception as e:
            logger.error("不明エラー")
            print("不明エラー", e)
        time.sleep(sleep_time)


def check_alive():
    HOST = '127.0.0.1'
    PORT = 54321
    heart_beat_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    heart_beat_socket.bind((HOST, PORT))
    heart_beat_socket.settimeout(1)

    logger.info("死活監視システム起動...")

    card_reader_state = True
    system_state = True
    wait_timeMax = 10
    last_AliveTime = time.time()
    while True:
        try:
            data, addr = heart_beat_socket.recvfrom(100)
            last_AliveTime = time.time()
            if data.decode('utf-8') == "DEAD" and card_reader_state:

                logger.error("カードリーダーが指定台数分接続されていません")
                send_mail(
                    card_reader_mail_config["TITLE"], card_reader_mail_config["TEXT"])
                logger.info('カードリーダー異常')
                last_AliveTime = time.time()
                card_reader_state = False

            if data.decode('utf-8') == "ALIVE" and not card_reader_state:
                logger.info("カードリーダーが指定台数接続されました")
                card_reader_state = True

        except socket.timeout:
            pass

        passTime = time.time() - last_AliveTime
        if passTime > wait_timeMax:

            if system_state:
                logger.error("解錠システム異常")
                send_mail(system_mail_config["TITLE"],
                        system_mail_config["TEXT"])
                logger.info('システム異常')
                last_AliveTime = time.time()
                system_state = False

        elif not system_state:
            system_state = True
            logger.info("システム正常に戻りました")


def main():
    logger.info("⏱️ sesameのバッテリーとサーバー状態を確認中...")
    threading.Thread(target=check_sesame_battery).start()
    threading.Thread(target=check_alive).start()


if __name__ == "__main__":
    main()
