import wmi
import re
import os
from smartcard.System import readers
import json
import time
import pythoncom
import pywintypes


# 設定ファイル読み込み
def load_config():
    BASE_DIR = os.path.dirname(__file__) + "\\..\\..\\config"
    config_path = os.path.join(BASE_DIR, "usb_settings.json")

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_serials():

    c = wmi.WMI()
    serials = []
    config = load_config()

    c = wmi.WMI()
    serials = []

    dev = config["devices"]
    for direction in ["入口", "出口"]:

        info = dev[direction]
        vid = info["vid"]
        pid = info["pid"]

        wql = f"SELECT DeviceID FROM Win32_PnPEntity WHERE DeviceID LIKE '%VID_{vid}&PID_{pid}%'"
        pattern = re.compile(
            rf"USB\\VID_{vid}&PID_{pid}(?:&MI_\d)?\\([^\\]+)$")

        for d in c.query(wql):
            m = pattern.search(d.DeviceID or "")
            if m:
                serials.append(m.group(1))

    return serials


def get_readers():
    start = time.time()
    config = load_config()
    desired_order = []
    devices = config["devices"]
    print(type(devices))
    for direction in ["入口", "出口"]:
        info = devices[direction]
        desired_order.append(info["serial"])

    r = readers()
    serials = get_all_serials()

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
    print(f"{time.time() - start}秒、全体")

    return ordered


# 実行例
if __name__ == "__main__":
    for reader, serial in get_readers():
        print(f"{reader} -> {serial}")
    print(get_all_serials())
