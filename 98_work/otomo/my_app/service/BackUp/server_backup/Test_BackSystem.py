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

import my_app.logs.log_config_service
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
from my_app.service.cardreader import CardReader
from my_app.service.utils.sendmail import send_mail
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

        card_reader_state = True
        system_state = True  # True=正常, False=已告警（异常中）
        waittimeMax = 10
        last_alive_time = time.time()

        DEAD_TIMES=0
        while True:
            try:
                data, addr = heartbeatsocket.recvfrom(100)  # 最多等1秒

                msg = data.decode('utf-8', 'ignore')
                logging.info(f"Sending heartbeat message: {msg}")

                last_alive_time = time.time()

                if msg == "DEAD" and card_reader_state:
                    logging.error("カードリーダーが指定台数分接続されていません")
                    send_mail(card_reader_mail_config["TITLE"], card_reader_mail_config["TEXT"])
                    card_reader_state = False
                    # 直接停机
                    break

                elif msg == "ALIVE":
                    # 收到心跳就认为系统恢复
                    if not card_reader_state:
                        logging.info("カードリーダが指定台数接続されました")
                        card_reader_state = True
                    if not system_state:
                        logging.info("解錠システムが復旧しました")
                        system_state = True

            except socket.timeout:
                # 超时没收到包，继续往下做超时判断
                pass

            # 超过阈值：只在“从正常 -> 异常”的瞬间触发一次
            pass_time = time.time() - last_alive_time
            if pass_time > waittimeMax and system_state:
                print("経過時間"+str(pass_time)+">"+str(waittimeMax)+"秒")
                logging.error("経過時間"+str(pass_time)+">"+str(waittimeMax)+"秒"+"解錠システム異常")
                send_mail(system_mail_config["TITLE"], system_mail_config["TEXT"])
                print('システム異常')
                system_state = False
                # 触发重启
                self.reopen_card_check()
                DEAD_TIMES+=1

            if DEAD_TIMES>=3:
                logging.error("解錠システム異常が3回発生しました、システムを停止します")
                break

            time.sleep(0.1)

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