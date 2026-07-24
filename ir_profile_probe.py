# ir_profile_probe.py — カメラプロファイル列挙(最後の隅っこ確認)
import sys, asyncio
print(f"実行中のPython: {sys.executable}")

from winrt.windows.media.capture.frames import (
    MediaFrameSourceGroup, MediaFrameSourceKind
)
from winrt.windows.media.capture import MediaCapture

def _sync(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def main():
    groups = _sync(MediaFrameSourceGroup.find_all_async())
    ir = [g for g in groups
          if any(s.source_kind == MediaFrameSourceKind.INFRARED
                 for s in g.source_infos)]
    ir.sort(key=lambda g: len(g.source_infos))
    target = ir[0]
    print(f"対象: {target.display_name}")

    # IRソースのデバイスIDを取得
    ir_info = next(s for s in target.source_infos
                   if s.source_kind == MediaFrameSourceKind.INFRARED)
    dev_id = ir_info.device_information.id
    print(f"DeviceID: {dev_id}\n")

    # プロファイル対応そのものを確認
    try:
        supported = MediaCapture.is_video_profile_supported(dev_id)
        print(f"プロファイル対応: {supported}")
    except Exception as e:
        print(f"is_video_profile_supported 失敗: {e}")
        supported = None

    if supported is False:
        print("→ このデバイスはプロファイル非対応。ここで終了。")
        return

    # 全プロファイル列挙
    try:
        profiles = MediaCapture.find_all_video_profiles(dev_id)
    except Exception as e:
        print(f"find_all_video_profiles 失敗: {e}")
        return

    print(f"\n=== プロファイル数: {len(list(profiles))} ===")
    for i, p in enumerate(profiles):
        print(f"\n[{i}] ID = {p.id}")
        try:
            descs = list(p.supported_record_media_description)
            print(f"    record: {len(descs)}件")
            for d in descs:
                print(f"      {d.width}x{d.height} @{d.frame_rate:.0f}fps "
                      f"{d.subtype}")
        except Exception as e:
            print(f"    record列挙失敗: {e}")

    print("\n※ IDに 'FaceAuth' を含むものがあれば当たり")

if __name__ == "__main__":
    main()