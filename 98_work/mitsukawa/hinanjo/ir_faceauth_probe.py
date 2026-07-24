# ir_faceauth_probe2.py — GET で FACEAUTH_MODE の正体を確認 → 正しい形式でSET
import sys, struct, time, asyncio
print(f"実行中のPython: {sys.executable}")

import winrt.windows.media.devices
from winrt.windows.media.capture.frames import (
    MediaFrameSourceGroup, MediaFrameSourceKind
)
from winrt.windows.media.capture import (
    MediaCapture, MediaCaptureInitializationSettings,
    MediaCaptureMemoryPreference, StreamingCaptureMode
)
from winrt.windows.storage.streams import Buffer
from winrt.windows.security.cryptography import CryptographicBuffer

GUID_EXT = struct.pack('<IHH8B', 0x1CB79112, 0xC0D2, 0x4213,
                       0x9C, 0xA6, 0xCD, 0x4F, 0xDB, 0x92, 0x79, 0x72)
KSPROPERTY_TYPE_GET = 0x00000001
KSPROPERTY_TYPE_SET = 0x00000002
FILTERSCOPE = 0xFFFFFFFF

SET_STATUS = {0: "SUCCESS", 1: "UnknownFailure", 2: "NotSupported",
              3: "InvalidValue", 4: "DeviceNotAvailable", 5: "NotInControl"}
GET_STATUS = {0: "SUCCESS", 1: "UnknownFailure", 2: "BufferTooSmall",
              3: "NotSupported", 4: "DeviceNotAvailable",
              5: "MaxSizeTooBig", 6: "MaxSizeRequired"}

def ksprop(prop_id, type_flag):
    return GUID_EXT + struct.pack('<II', prop_id, type_flag)

def header(flags, pin_id, size):
    return struct.pack('<IIIIQQ', 1, pin_id, size, 0, flags, 0)

def _sync(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

latest_mean = [None]

def on_frame(sender, args):
    try:
        ref = sender.try_acquire_latest_frame()
        if ref is None or ref.video_media_frame is None:
            return
        bmp = ref.video_media_frame.software_bitmap
        if bmp is None:
            return
        n = bmp.pixel_width * bmp.pixel_height
        buf = Buffer(n * 2)
        bmp.copy_to_buffer(buf)
        data = bytes(CryptographicBuffer.copy_to_byte_array(buf))  # ★bytes化
        step = max(1, n // 2000)
        sample = data[:n:step]
        latest_mean[0] = round(sum(sample) / len(sample), 1)
    except Exception as e:
        latest_mean[0] = f"err:{e}"

def try_get(vdc, pid):
    """GETしてヘッダをデコード。(status, flags, capability) を返す"""
    res = vdc.get_device_property_by_extended_id(
        ksprop(pid, KSPROPERTY_TYPE_GET), 40)
    st = int(res.status)
    if st != 0:
        return st, None, None
    raw = bytes(res.value) if res.value is not None else b""
    if len(raw) >= 32:
        ver, pin, size, result, flags, cap = struct.unpack_from('<IIIIQQ', raw)
        return st, flags, cap
    return st, None, None

def main():
    groups = _sync(MediaFrameSourceGroup.find_all_async())
    ir_groups = [g for g in groups
                 if any(s.source_kind == MediaFrameSourceKind.INFRARED
                        for s in g.source_infos)]
    ir_groups.sort(key=lambda g: len(g.source_infos))
    target = ir_groups[0]
    print(f"対象: {target.display_name}")

    settings = MediaCaptureInitializationSettings()
    settings.source_group = target
    settings.memory_preference = MediaCaptureMemoryPreference.CPU
    settings.streaming_capture_mode = StreamingCaptureMode.VIDEO
    mc = MediaCapture()
    _sync(mc.initialize_with_settings_async(settings))

    ir_source = next(s for _i, s in mc.frame_sources.items()
                     if s.info.source_kind == MediaFrameSourceKind.INFRARED)
    reader = _sync(mc.create_frame_reader_async(ir_source))
    reader.add_frame_arrived(on_frame)
    _sync(reader.start_async())
    time.sleep(2.0)
    print(f"【設定前】frame_mean ≈ {latest_mean[0]}\n")

    vdc = mc.video_device_controller

    # ─── Phase 1: GETで正体確認 ───
    print("=== GET probe (id 30-40) ===")
    candidates = []
    for pid in range(30, 41):
        st, flags, cap = try_get(vdc, pid)
        label = GET_STATUS.get(st, st)
        if st == 0:
            print(f"  id={pid}: GET SUCCESS  Flags={flags:#x} Capability={cap:#x} ★")
            candidates.append((pid, flags, cap))
        elif st != 3:  # NotSupported以外は面白いので表示
            print(f"  id={pid}: {label}")

    if not candidates:
        print("\nGETも全滅。ドライバはFrameServer経由の拡張制御を非公開にしてる。")
        print("→ 弾3(DirectShow/UVC XU)へ進む。")
        _sync(reader.stop_async())
        return

    # ─── Phase 2: Capabilityに載ってるフラグをSET ───
    print("\n=== SET (Capabilityに基づく) ===")
    for pid, cur_flags, cap in candidates:
        for flag in (0x2, 0x4):        # ALT_ILLUM, BG_SUB
            if not (cap & flag):
                continue               # ドライバが非対応のフラグは送らない
            for size in (40, 32):      # ヘッダ+VALUE / ヘッダのみ
                pay = header(flag, FILTERSCOPE, size)
                if size == 40:
                    pay += struct.pack('<Q', 0)
                st = int(vdc.set_device_property_by_extended_id(
                    ksprop(pid, KSPROPERTY_TYPE_SET), pay))
                print(f"  id={pid} flag={flag:#x} size={size}"
                      f" → {SET_STATUS.get(st, st)}")
                if st == 0:
                    print("\n★★ SET SUCCESS! LED点灯効果を測定 ★★")
                    for i in range(10):
                        time.sleep(1)
                        print(f"    t+{i+1}s frame_mean ≈ {latest_mean[0]}")
                    _sync(reader.stop_async())
                    return

    print("\nSETは通らなかったが、GETの結果(上のFlags/Capability)を報告して。")
    _sync(reader.stop_async())

if __name__ == "__main__":
    main()