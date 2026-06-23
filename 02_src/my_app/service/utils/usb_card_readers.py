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


def same_get_serials():

    c = wmi.WMI()
    serials = []
    config = load_config()

    dev = config["devices"]
    try:
        info = dev["入口"]
    except Exception:
        info = dev["出口"]
    vid = info["vid"]
    pid = info["pid"]
    s = info["serial"]
    if s.isdigit():
        serial_regex = rf"\d{{{len(s)}}}"
    else:
        # 使用されている文字だけを許容する
        serial_regex = "[" + "".join(sorted(set(s))) + "]+"

    wql = f"SELECT DeviceID FROM Win32_PnPEntity WHERE DeviceID LIKE '%VID_{vid}&PID_{pid}%'"
    pattern = re.compile(
        rf"USB\\VID_{vid}&PID_{pid}\\({serial_regex})$")

    for d in c.query(wql):
        m = pattern.search(d.DeviceID or "")
        if m:
            serials.append(m.group(1))

    return serials


def get_readers():
    start = time.time()
    config = load_config()
    desired_order = []
    pid_list = []
    vid_list = []
    name_list = []
    devices = config["devices"]
    print(type(devices))
    for direction in ["入口", "出口"]:
        info = devices[direction]
        desired_order.append(info["serial"])
        pid_list.append(info["pid"])
        vid_list.append(info["vid"])
        name_list.append(info["name"])

    r = readers()
    reader_serial_map = {}
    if (len(desired_order) == 1) or (len(desired_order) > 1 and pid_list[0] == pid_list[1] and vid_list[0] == vid_list[1]):
        serials = same_get_serials()

        for i, reader in enumerate(r):
            if i < len(serials):
                reader_serial_map[reader] = serials[i]
            else:
                reader_serial_map[reader] = None

    else:
        # カードリーダーの種類が違うときの処理まだ未実装
        for reader in r:
            for i in range(len(name_list)):
                if str(reader) == name_list[i]:
                    reader_serial_map[reader] = desired_order[i]

                else:
                    reader_serial_map[reader] = None

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
    print(same_get_serials())
