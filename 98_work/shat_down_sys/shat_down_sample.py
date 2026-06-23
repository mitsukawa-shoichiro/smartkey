import json
import time
from datetime import datetime
import os
import logging

CONFIG_FILE = "setting_shat_down.json"

"""
    
"""


def should_reboot(config):
    now = datetime.now()
    reboot_time = config.get("reboot_time", "")
    reboot_done_date = config.get("reboot_done_date", "")
    reboot_status = config.get("reboot_status", "")

    reboot_hour, reboot_minute = map(int, reboot_time.split(":"))

    # 時刻チェック
    if now.hour == reboot_hour and now.minute == reboot_minute:
        # 今日まだ再起動していなければTrue
        if reboot_done_date != now.strftime("%Y-%m-%d"):
            # 設定がオンかどうか
            if reboot_status == "True":
                return True
    return False


def set_reboot_done(config):
    config["reboot_done_date"] = datetime.now().strftime("%Y-%m-%d")
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def main_loop():
    while True:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            if should_reboot(config):
                logging.info("指定時刻です。Windowsを再起動します。")
                set_reboot_done(config)
                os.system("shutdown /r /t 0")
        print(should_reboot(config))
        time.sleep(30)


if __name__ == "__main__":
    main_loop()
