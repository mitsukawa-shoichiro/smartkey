import logging
import requests
import time
import socket
import threading
import os
import sys
import json
LOGS_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..'))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)

import logs.log_config_service
# region Read Config
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(
    __file__), '..',  'config', 'backend', 'backendsys.json'))
print(CONFIG_PATH)
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_list = json.load(f)
    battery_config = config_list["battery_observation"]
    battery_mail_config = config_list["battery_mail"]
    sesame_mail_config = config_list["sesame_mail"]
    card_reader_mail_config = config_list["cardreader_mail"]
    system_mail_config = config_list["system_mail"]

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(
    __file__), '..',  'config', 'backend', 'sesami_config.json'))
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_list = json.load(f)
    sesami_config = config_list["device"]


sesame_id = sesami_config["sesame_id"]
x_api_key = sesami_config["x_api_key"]

sleep_time = int(battery_config["sleep_time"])
battery_Limit = int(battery_config["battery_limit"])  # バッテリー残量の閾値
# endregion
from service.cardreader import CardReader
from service.utils.sendmail import send_mail
class BackSystem():
    HOST = '127.0.0.1'
    PORT = 54321

    cardReader: CardReader 
    backsystem_instance: "BackSystem"
    def __init__(self):
        print("⏱️ sesameのバッテリーとサーバー状態を確認中...")
        self.cardReader = CardReader()
        self.cardReader.start_thread()
        threading.Thread(target=self.check_sesame_battery).start()
        threading.Thread(target=self.check_alive).start()
        BackSystem.backsystem_instance = self
        logging.info("BackSystem started.")

    def check_sesame_battery(self):
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

    def check_alive(self):

        heartbeatsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        heartbeatsocket.bind((self.HOST, self.PORT))
        heartbeatsocket.settimeout(1)

        print("死活監視システム起動...")


        DEAD_TIMES=0
        while True:
            if not self.cardReader.check_is_alive():
                print(self.cardReader.check_is_alive())
                print("カードリーダースレッドが停止しているため再起動します")
                self.reopen_card_check()
                DEAD_TIMES+=1
            
            if DEAD_TIMES>=5:
                logging.error("解錠システム異常が3回発生しました、システムを停止します")
                mailText = "解錠システム異常が3回発生しました、システムを停止します、確認してください"
                mailTitle="カード認証システム異常"
                send_mail( mailTitle,mailText)
                break
        
            time.sleep(1)

    def reopen_card_check(self):
        if not self.cardReader.check_is_alive():
            self.cardReader.start_thread()
            logging.info("カードリーダースレッドを再起動しました。")

    def stop(self):
        self.cardReader.stop_thread()
        logging.info("BackSystem stopped.")




def main():
    BackSystem()
    
if __name__ == "__main__":
    BackSystem()