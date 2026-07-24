# ir_led_probe.py v2  (サービス停止後に単独実行)
import sys
print(f"実行中のPython: {sys.executable}")
import asyncio
from winrt.windows.media.capture.frames import (
    MediaFrameSourceGroup, MediaFrameSourceKind
)
from winrt.windows.media.capture import (
    MediaCapture, MediaCaptureInitializationSettings,
    MediaCaptureMemoryPreference, StreamingCaptureMode
)
import winrt.windows.media.devices  # ← これが重要(プロジェクション登録)
from winrt.windows.media.devices import InfraredTorchMode

def _sync(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def main():
    groups = _sync(MediaFrameSourceGroup.find_all_async())
    ir_groups = []
    print("=== 検出カメラグループ ===")
    for g in groups:
        kinds = [s.source_kind for s in g.source_infos]
        print(f"  {g.display_name}: {[str(int(k)) for k in kinds]}")
        if any(k == MediaFrameSourceKind.INFRARED for k in kinds):
            ir_groups.append(g)
            print("  ↑ IRカメラあり ★")

    if not ir_groups:
        print("\nIRカメラが見つかりません")
        return

    # IRのみの単独グループを優先(合成グループYourCameraGroupは後回し)
    ir_groups.sort(key=lambda g: len(g.source_infos))
    target = ir_groups[0]
    print(f"\n対象: {target.display_name}")

    settings = MediaCaptureInitializationSettings()
    settings.source_group = target
    settings.memory_preference = MediaCaptureMemoryPreference.CPU
    settings.streaming_capture_mode = StreamingCaptureMode.VIDEO

    mc = MediaCapture()
    try:
        # ★修正: pywinrtではオーバーロードが別名になる
        _sync(mc.initialize_with_settings_async(settings))
        print("✓ MediaCapture 初期化OK")
    except AttributeError:
        # 万一メソッド名が違う場合の確認用
        cand = [m for m in dir(mc) if "initialize" in m.lower()]
        print(f"✗ メソッド名不一致。候補: {cand}")
        return
    except Exception as e:
        print(f"✗ 初期化失敗: {type(e).__name__}: {e}")
        return

# ─── InfraredTorchControl 確認 ─────────────────
    vdc = mc.video_device_controller
    print(f"\nVideoDeviceController 型: {type(vdc)}")

    try:
        ir_ctrl = vdc.infrared_torch_control
        print("✓ infrared_torch_control 取得OK")
    except Exception as e:
        print(f"✗ 取得失敗: {type(e).__name__}: {e}")
        # 何が生えてるか確認
        cand = [m for m in dir(vdc) if "torch" in m.lower() or "infrared" in m.lower()]
        print(f"  torch/infrared 系の属性: {cand}")
        return

    print("\n=== InfraredTorchControl ===")
    print(f"IsSupported : {ir_ctrl.is_supported}")

    if not ir_ctrl.is_supported:
        print("→ IRTORCHMODE 未実装。弾2(FACEAUTH_MODE)へ進む")
        return

    from winrt.windows.media.devices import InfraredTorchMode
    print(f"SupportedModes: {[str(m) for m in ir_ctrl.supported_modes]}")
    print(f"CurrentMode   : {ir_ctrl.current_mode}")
    print(f"Power         : {ir_ctrl.power} / max {ir_ctrl.max_power}")

    try:
        ir_ctrl.current_mode = InfraredTorchMode.ON
        print("→ InfraredTorchMode.ON 設定成功")
    except Exception as e:
        print(f"ON 失敗 ({e}) → 交互点灯モードを試行")
        ir_ctrl.current_mode = InfraredTorchMode.ALTERNATING_FRAME_ILLUMINATION

    ir_ctrl.power = ir_ctrl.max_power
    print(f"\n✓ 設定完了: mode={ir_ctrl.current_mode}, power={ir_ctrl.power}")
    print("スマホカメラでIR発光を目視確認してください。")
    input("Enterで終了...")

if __name__ == "__main__":
    main()