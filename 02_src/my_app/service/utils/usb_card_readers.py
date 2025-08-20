import wmi
import re
import os
from smartcard.System import readers
import json

import pythoncom
import pywintypes



# 設定ファイル読み込み
def load_config():
     BASE_DIR = os.path.dirname(__file__) + "\\..\\..\\config"
     config_path = os.path.join(BASE_DIR, "usb_settings.json")


     with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_serials():
    """PaSoRiシリアル番号リストを取得"""
    c = wmi.WMI()
    serials = []
    for dev in c.Win32_PnPEntity():
        if "VID_054C&PID_0DC9" in (dev.DeviceID or ""):
            m = re.search(
                r"USB\\VID_054C&PID_0DC9(?:&MI_\d)?\\([^\\]+)$", dev.DeviceID)
            if m:
                serials.append(m.group(1))
    return serials


def get_readers():
   
    config = load_config()
    desired_order = list(config.values())  # 例: ["0373604","0371756"]

    r = readers()  # pyscard で取得
    serials = get_all_serials()  # WMI で取得

    # pyscard reader に serial を順番に割り当て
    reader_serial_map = {}
    for i, reader in enumerate(r):
        if i < len(serials):
            reader_serial_map[reader] = serials[i]
        else:
            reader_serial_map[reader] = None

    # 設定順に並べ替え
    ordered = sorted(
        reader_serial_map.items(),
        key=lambda x: desired_order.index(
            x[1]) if x[1] in desired_order else len(desired_order)
    )

    return ordered


# 実行例
if __name__ == "__main__":
    for reader, serial in get_readers():
        print(f"{reader} -> {serial}")
