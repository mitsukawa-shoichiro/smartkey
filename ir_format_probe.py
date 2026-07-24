# ir_format_probe.py — フォーマット切替でLEDが点くか検証
import sys, time, asyncio
print(f"実行中のPython: {sys.executable}")

from winrt.windows.media.capture.frames import (
    MediaFrameSourceGroup, MediaFrameSourceKind
)
from winrt.windows.media.capture import (
    MediaCapture, MediaCaptureInitializationSettings,
    MediaCaptureMemoryPreference, MediaCaptureSharingMode,
    StreamingCaptureMode
)
from winrt.windows.storage.streams import Buffer
from winrt.windows.security.cryptography import CryptographicBuffer

def _sync(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

state = {"mean": None, "peak": 0.0, "frames": 0}

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
        data = bytes(CryptographicBuffer.copy_to_byte_array(buf))
        step = max(1, n // 2000)
        s = data[:n:step]
        m = round(sum(s) / len(s), 1)
        state["mean"] = m
        state["peak"] = max(state["peak"], m)
        state["frames"] += 1
    except Exception:
        pass

def main():
    groups = _sync(MediaFrameSourceGroup.find_all_async())
    ir = [g for g in groups
          if any(s.source_kind == MediaFrameSourceKind.INFRARED
                 for s in g.source_infos)]
    ir.sort(key=lambda g: len(g.source_infos))
    target = ir[0]
    print(f"対象: {target.display_name}")

    # ★ExclusiveControl: フォーマット変更に必要
    settings = MediaCaptureInitializationSettings()
    settings.source_group = target
    settings.sharing_mode = MediaCaptureSharingMode.EXCLUSIVE_CONTROL
    settings.memory_preference = MediaCaptureMemoryPreference.CPU
    settings.streaming_capture_mode = StreamingCaptureMode.VIDEO

    mc = MediaCapture()
    try:
        _sync(mc.initialize_with_settings_async(settings))
    except Exception as e:
        print(f"✗ 初期化失敗: {e}")
        print("  → 他のアプリがカメラを掴んでる。smartkeyサービス停止 & ロック解除して再試行")
        return
    print("✓ ExclusiveControl 初期化OK\n")

    src = next(s for _i, s in mc.frame_sources.items()
               if s.info.source_kind == MediaFrameSourceKind.INFRARED)

    # ─── フォーマット一覧 ───
    print("=== 対応フォーマット ===")
    fmts = list(src.supported_formats)
    for i, f in enumerate(fmts):
        vf = f.video_format
        fps = f.frame_rate.numerator / max(1, f.frame_rate.denominator)
        print(f"  [{i:2d}] {f.subtype:6s} {vf.width}x{vf.height} @{fps:.0f}fps")

    cur = src.current_format
    print(f"\n現在: {cur.subtype} {cur.video_format.width}x"
          f"{cur.video_format.height} "
          f"@{cur.frame_rate.numerator/max(1,cur.frame_rate.denominator):.0f}fps")

    reader = _sync(mc.create_frame_reader_async(src))
    reader.add_frame_arrived(on_frame)
    _sync(reader.start_async())

    # ─── 各フォーマットで測定 ───
    print("\n=== フォーマット別 frame_mean ===")
    for i, f in enumerate(fmts):
        vf = f.video_format
        fps = f.frame_rate.numerator / max(1, f.frame_rate.denominator)
        try:
            _sync(src.set_format_async(f))
        except Exception as e:
            print(f"  [{i:2d}] 切替失敗: {e}")
            continue
        state["mean"] = None
        state["frames"] = 0
        time.sleep(3)
        mark = " ★★★" if (state["mean"] or 0) > 10 else ""
        print(f"  [{i:2d}] {f.subtype:6s} {vf.width}x{vf.height} @{fps:.0f}fps"
              f"  → mean={state['mean']}  frames={state['frames']}{mark}")

    _sync(reader.stop_async())
    print(f"\n最大 frame_mean = {state['peak']}")

if __name__ == "__main__":
    main()