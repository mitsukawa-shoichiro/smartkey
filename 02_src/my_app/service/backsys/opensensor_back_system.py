import sys
import os

# 絶対パスで PROJECT_ROOT を指定
PROJECT_ROOT = r"C:\smartkey\02_src"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

print("=== DEBUG INFO ===")
print("PROJECT_ROOT:", PROJECT_ROOT)
print("sys.path:")
for i, p in enumerate(sys.path):
    print(f"  [{i}] {p}")

# my_app ディレクトリの存在確認
my_app_path = os.path.join(PROJECT_ROOT, "my_app")
print("my_app exists:", os.path.exists(my_app_path))
if os.path.exists(my_app_path):
    print("my_app contents:", os.listdir(my_app_path))

# logs ディレクトリの確認
logs_path = os.path.join(my_app_path, "logs")
print("logs exists:", os.path.exists(logs_path))
if os.path.exists(logs_path):
    print("logs contents:", os.listdir(logs_path))

# log_config_service モジュールの確認
log_config_path = os.path.join(logs_path, "log_config_service.py")
print("log_config_service.py exists:", os.path.exists(log_config_path))

# インポートを試みる
try:
    import my_app.logs.log_config_service
    print("✅ my_app.logs.log_config_service imported successfully")
except Exception as e:
    print("❌ Import error:", e)
    import traceback
    traceback.print_exc()


import logging
import requests
import time
import select
import signal
import socket
from my_app.service.backsys.sendmail import send_mail
import threading
import json

#4階層上の絶対パスを取得してモジュール検索パスの先頭に追加する
LOGS_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..','..','..'))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)

#設定パス(絶対パス)
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(
    __file__), '..', '..', 'config', 'backend', 'backendsys.json'))
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_list = json.load(f)
    battery_config = config_list["battery_observation"]
    battery_mail_config = config_list["battery_mail"]
    open_sensor_mail_config = config_list["open_sensor_mail"]
    # card_reader_mail_config = config_list["card_reader_mail"]
    system_mail_config = config_list["system_mail"]

#プロジェクト内の設定ファイルからデバイス部分を読込
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(
    __file__), '..', '..', 'config', 'backend', 'open_sensor_config.json'))
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_list = json.load(f)
    open_sensor_config = config_list["device"]

open_sensor_id = open_sensor_config["open_sensor_id"]
x_api_key = open_sensor_config["x_api_key"]

sleep_time = int(battery_config["sleep_time"])
battery_Limit = int(battery_config["battery_limit"])  # バッテリー残量の閾値

logger = logging.getLogger(__name__)  # logに書き込む用

stop_event = threading.Event()

#利用可能なポート番号を探す
def find_available_port(start_port=54321, max_tries=10):
    for port in range(start_port, start_port + max_tries):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind(('127.0.0.1', port))
            s.close()
            return port
        except OSError:
            continue
    raise RuntimeError(f"ポート {start_port}〜{start_port+max_tries-1} がすべて使用中です")

HOST = '127.0.0.1'
PORT = find_available_port()

def check_open_sensor_battery():
    '''
    # open_sensorのバッテリー残量を確認し、50%以下ならメールを送信する

    '''
    logger.info("check_sesame_battery 開始")
    battery_state = True
    open_sensor_state = True
    
    while  not stop_event.is_set():
        logger.debug("check_sesame_battery ループ開始")
        try:
            logger.debug("open_sensor API リクエスト開始")
            open_sensor_url = f"https://app.candyhouse.co/api/sesame2/{open_sensor_id}"
            headers = {"x-api-key": x_api_key}
            response = requests.get(open_sensor_url, headers = headers, timeout = 10)   #10秒でタイムアウト

            logger.debug("open_sensor API リクエスト完了")
            
            logger.debug("JSON 解析開始")
            try:
                data = response.json()
                battery = data.get('batteryPercentage', '取得失敗')
            except Exception as e:
                battery = f"JSON解析失敗: {e}"
                logger.error("JSON 解析エラー", exc_info=True)
            logger.debug("JSON 解析完了")

            logger.debug(f"バッテリー残量: {battery}")
            logger.info(f"バッテリー残量: {battery}")
            logger.debug(f"wm2State: {data.get('wm2State', '取得失敗')}")

            logger.debug("バッテリー閾値チェック開始")
            try:
                #バッテリーが既定値以下になった時のメッセージ
                if float(battery) <= battery_Limit:
                    logger.error(f"バッテリーが{battery_Limit}%以下になりました。")

                    if battery_state:
                        logger.debug("バッテリー警告メール送信開始")
                        mailText = battery_mail_config["TEXT"] + response.text
                        send_mail_async(battery_mail_config["TITLE"], mailText)
                        logger.debug("バッテリー警告メール送信完了")
                        battery_state = False

                elif not battery_state:
                    logger.info(f"バッテリーが{battery_Limit}%以上に戻りました。")
                    battery_state = True
                #セサミのデータを取得失敗したとき
                logger.debug("セサミ接続状態チェック開始")
                wm2_state = data.get('wm2State')
                if wm2_state is None or wm2_state == '':
                    logger.error("セサミと接続できません")

                    if open_sensor_state:
                        logger.debug("オープンセンサー接続エラーメール送信開始")
                        mailText = battery_mail_config["TEXT"] + response.text
                        send_mail_async(
                            open_sensor_mail_config["TITLE"], open_sensor_mail_config["TEXT"])
                        logger.debug("オープンセンサー接続エラーメール送信完了")
                        open_sensor_state = False

                elif not open_sensor_state:
                    logger.info("オープンセンサーとの接続が回復しました")
                    open_sensor_state = True
                logger.debug("オープンセンサー接続状態チェック完了")

            except Exception as e:
                logger.error("メール送信エラー")
                logger.debug(f"メール送信エラー: {e}")

        except Exception as e:
            logger.error("不明エラー", exc_info=True)
            print("不明エラー", e)
        logger.debug("check_sesame_battery ループ終了")
        
        # sleep_time 秒待機（stop_event がセットされたら即座に復帰）
        stop_event.wait(sleep_time)

    logger.info("check_sesame_battery 終了")

#利用可能なポート番号を探す
def send_mail_async(title, body):
    def _send():
        try:
            send_mail(title, body)
        except Exception as e:
            logger.error("メール送信エラー", exc_info=True)

    t = threading.Thread(target=_send, daemon=True)
    t.start()

    #例外処理を確実にログに残すための文
    # except Exception as e:
    #     logger.exception("🔥 Thread 内で例外発生")
    # finally:
    #     logger.info("🛑 worker stopped")

threads = []

def main():
    logger.info("⏱️ open_sensorのバッテリーとサーバー状態を確認中...")
    threads.append(threading.Thread(target=check_open_sensor_battery))
    # threads.append(threading.Thread(target=check_alive))
    for t in threads:
        t.start()
    # t = threading.Thread(target=check_open_sensor_battery, daemon=False)
    # t.start()
    # threading.Thread(target=check_alive).start()

    try:
        # stop_event がセットされるまで待機（Ctrl+C で KeyboardInterrupt が発生）
        stop_event.wait()

    except KeyboardInterrupt:
        logger.info("Ctrl+Cを受信しました。終了します。")
        stop_event.set()

    for t in threads:
            t.join()

# Windows では、SIGINT をデフォルト動作（KeyboardInterrupt を投げる）に戻す
signal.signal(signal.SIGINT, signal.SIG_DFL)

if __name__ == "__main__":
    main()