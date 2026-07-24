# ir_shared_probe.py — Hello点灯中のフレームを相乗り取得できるか検証
import sys, time, asyncio
print(f"実行中のPython: {sys.executable}")

from winrt.windows.media.capture.frames import (
    MediaFrameSourceGroup, MediaFrameSourceKind
)
from winrt.windows.media.capture import (
    MediaCapture, MediaCaptureInitializationSettings,
    MediaCaptureMemoryPreference, MediaCaptureSharingMode
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
    except Exception as e:
        state["mean"] = f"err:{e}"

def main():
    groups = _sync(MediaFrameSourceGroup.find_all_async())
    ir = [g for g in groups
          if any(s.source_kind == MediaFrameSourceKind.INFRARED
                 for s in g.source_infos)]
    ir.sort(key=lambda g: len(g.source_infos))
    target = ir[0]
    print(f"対象: {target.display_name}")

    # ★SharedReadOnly: 他アプリ(Hello)が握っていても読める
    settings = MediaCaptureInitializationSettings()
    settings.source_group = target
    settings.sharing_mode = MediaCaptureSharingMode.SHARED_READ_ONLY
    settings.memory_preference = MediaCaptureMemoryPreference.CPU

    mc = MediaCapture()
    _sync(mc.initialize_with_settings_async(settings))
    print("✓ SharedReadOnly で初期化OK")

    src = next(s for _i, s in mc.frame_sources.items()
               if s.info.source_kind == MediaFrameSourceKind.INFRARED)
    reader = _sync(mc.create_frame_reader_async(src))
    reader.add_frame_arrived(on_frame)
    _sync(reader.start_async())

    print("\n" + "=" * 50)
    print("60秒間モニタします。この間に別ウィンドウで:")
    print("  Win+L でロック → カメラを見て Windows Hello を走らせる")
    print("  (何度かやってOK。LEDが光る瞬間を狙う)")
    print("=" * 50 + "\n")

    for i in range(300):
        time.sleep(1)
        print(f"  t+{i+1:2d}s  mean={state['mean']}"
              f"  peak={state['peak']}  frames={state['frames']}")

    _sync(reader.stop_async())
    print(f"\n=== 結果 ===")
    print(f"最大 frame_mean = {state['peak']}")
    if state["peak"] > 8:
        print("★ 相乗り成功。Hello点灯中の映像を取得できている")
    else:
        print("→ 数値が上がらず。Hello中はフレームが遮断されている可能性")

if __name__ == "__main__":
    main()