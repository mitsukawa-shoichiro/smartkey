"""
リーダー状態管理モジュール
WMIを使ってリーダーを認識するのは時間がかかってしまうので基本キャッシュで節約
"""
import logging
import re
import threading

from smartcard.System import readers
from my_app.config.reader_config import DEVICES, norm_serial

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_cached_names = None    # 前回解決したときのリーダー名一覧
_cached_result = []     # [(reader, serial), ...]


def resolve_readers():
    """
    [(reader, serial), ...] を設定(DEVICES)の記載順で返す。

    PC/SCのリーダー名一覧が前回と同じ間はキャッシュを返すため、
    定常状態ではWMIを呼ばない。抜き差しで一覧が変わったときだけ
    _resolve()が走る。
    """
    global _cached_names, _cached_result

    current = readers()                       # ここは軽い
    names = tuple(str(r) for r in current)

    with _lock:
        if names != _cached_names:
            logger.info("リーダー構成の変化を検出: %s", list(names))
            _cached_result = _resolve(current, names)
            _cached_names = names
        return list(_cached_result)


def _resolve(current, names):
    """
    リーダーとserialの対応を決める。抜き差し時のみ呼ばれる想定。
    """
    # 1) config に reader_name があれば、それで確定(WMI不要)
    if all(d.get("reader_name") for d in DEVICES.values()):
        by_name = {str(r): r for r in current}
        result = []
        for direction, info in DEVICES.items():
            rd = by_name.get(info["reader_name"])
            if rd is None:
                logger.error("リーダーが見つかりません: %s (%s)",
                             info["reader_name"], direction)
                continue
            result.append((rd, info["serial"]))
            logger.info("リーダー確定: %s -> %s (serial=%s)",
                        info["reader_name"], direction, info["serial"])
        return result

    # 2) reader_name 未設定 → WMIでserialを引いて順序で対応づける(推測)
    return _resolve_by_wmi(current, names)


def _resolve_by_wmi(current, names):
    serials = _query_serials()

    if len(serials) != len(current):
        logger.error(
            "リーダー数とserial数が不一致 (readers=%d, serials=%d)。"
            "対応づけに失敗した可能性があります: %s",
            len(current), len(serials), serials)

    known = {d["serial"] for d in DEVICES.values() if d["serial"]}
    result = []
    for i, rd in enumerate(current):
        serial = serials[i] if i < len(serials) else None
        if serial is None or serial not in known:
            logger.error("serialを特定できないリーダーを除外: %s (serial=%r)",
                         names[i], serial)
            continue
        result.append((rd, serial))
        logger.warning("リーダー推定: %s -> serial=%s "
                       "(順序による推測。入退室が逆なら要確認)", names[i], serial)

    # DEVICESの記載順に並べ替える
    order = [d["serial"] for d in DEVICES.values()]
    result.sort(key=lambda x: order.index(x[1]) if x[1] in order else len(order))
    return result


def _query_serials():
    """
    Win32_PnPEntityからUSBシリアルを取得する。重いので抜き差し時のみ。
    """
    import wmi
    import pythoncom

    pythoncom.CoInitialize()
    try:
        first = next(iter(DEVICES.values()), None)
        if first is None:
            return []
        vid, pid = first["vid"], first["pid"]

        wql = (f"SELECT DeviceID FROM Win32_PnPEntity "
               f"WHERE DeviceID LIKE '%VID_{vid}&PID_{pid}%'")
        pattern = re.compile(
            rf"USB\\VID_{vid}&PID_{pid}\\([0-9A-Fa-f]+)$", re.IGNORECASE)

        found = []
        for d in wmi.WMI().query(wql):
            m = pattern.search(d.DeviceID or "")
            if m:
                found.append(norm_serial(m.group(1)))

        found.sort()   # WMIの返却順は未定義なので、せめて決定的にする
        return found
    except Exception:
        logger.exception("WMIによるserial取得に失敗")
        return []
    finally:
        pythoncom.CoUninitialize()