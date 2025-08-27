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

    info1 = dev["a"]
    vid1 = info1["vid"]
    pid1 = info1["pid"]
    s1 = info1["serial"]
    if s1.isdigit():
        serial_regex1 = rf"\d{{{len(s1)}}}"
    else:
        # 使用されている文字だけを許容する
        serial_regex1 = "[" + "".join(sorted(set(s1))) + "]+"
    info2 = dev["b"]
    vid2 = info2["vid"]
    pid2 = info2["pid"]
    s2 = info2["serial"]
    if s2.isdigit():
        serial_regex2 = rf"\d{{{len(s2)}}}"
    else:
        # 使用されている文字だけを許容する
        serial_regex2 = "[" + "".join(sorted(set(s2))) + "]+"

    wql = (
        f"SELECT DeviceID FROM Win32_PnPEntity WHERE DeviceID LIKE '%VID_{vid1}&PID_{pid1}%' OR DeviceID LIKE '%VID_{vid2}&PID_{pid2}%'"
    )
    pattern1 = re.compile(
        rf"USB\\VID_{vid1}&PID_{pid1}\\({serial_regex1})$", re.IGNORECASE)
    pattern2 = re.compile(
        rf"USB\\VID_{vid2}&PID_{pid2}\\({serial_regex2})$", re.IGNORECASE)

    for d in c.query(wql):
        devid = d.DeviceID or ""
        m1 = pattern1.search(devid)
        m2 = pattern2.search(devid)
        if m1:
            serials.append(m1.group(1))
        elif m2:
            serials.append(m2.group(1))

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
    # print(get_all_serials())
