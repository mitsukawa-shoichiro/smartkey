import asyncio
import threading
import time
import numpy as np

from winrt.windows.graphics.imaging import BitmapPixelFormat
from winrt.windows.media.capture import (
    MediaCapture,
    MediaCaptureInitializationSettings,
    MediaCaptureMemoryPreference,
    MediaCaptureSharingMode,
    StreamingCaptureMode,
)

from winrt.windows.media.capture.frames import (
    MediaFrameReaderStartStatus,
    MediaFrameSourceGroup,
    MediaFrameSourceKind,
)
from winrt.windows.storage.streams import Buffer


class MediaFoundationIRCamera:
    """
    Media FoundationからIR画像を取得する
    """
    def __init__(self, device_id_contains, startup_timeout = 5.0, max_age_ms = 150.0):
        self.device_id_contains = device_id_contains.upper()
        self.startup_timeout = float(startup_timeout)
        self.max_age_ms = float(max_age_ms)

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()
        self._thread = None

        self._latest_frame = None
        self._latest_at = 0.0
        self._grabbed_frame = None
        self._opened = False

        self.last_error = None
        self.group_name = None
        self.source_id = None

        self.start()
    
    def start(self):
        """
        IR取得用スレッドを開始
        """
        if self._thread is not None and self._thread.is_alive():
            return self.isOpened()
        
        self._stop_event.clear()
        self._ready_event.clear()
        self.last_error = None

        self._thread = threading.Thread(
            target = self._thread_main,
            name = "MediaFoundationIRCamera",
            daemon = True
        )
        self._thread.start()

        self._ready_event.wait(self.startup_timeout)

        if not self.isOpened():
            self.release()
            return False
        
        return True
    
    def isOpened(self):
        return (self._opened and self._thread is not None and self._thread.is_alive())
    
    def grab(self):
        """
        最新IRフレームを取得対象として固定
        """
        with self._lock:
            if self._latest_frame is None:
                self._grabbed_frame = None
                return False

            age_ms = (time.monotonic() - self._latest_at) * 1000

            if age_ms > self.max_age_ms:
                self._grabbed_frame = None
                return False
            
            self._grabbed_frame = self._latest_frame.copy()
            return True
        
    def retrieve(self):
        """
        grabで固定したIRフレームを返す
        """
        with self._lock:
            if self._grabbed_frame is None:
                return False, None
            
            return True, self._grabbed_frame.copy()
        
    def read(self):
        if not self.grab():
            return False, None
        
        return self.retrieve()
    
    def release(self):
        """
        IRカメラと取得スレッドを停止
        """
        self._stop_event.set()

        if (
            self._thread is not None
            and self._thread.is_alive()
            and self._thread is not threading.current_thread()
        ):
            self._thread.join(timeout = 3.0)

        self._opened = False

        with self._lock:
            self._latest_frame = None
            self._grabbed_frame = None
            self._latest_at = 0

        self._thread = None

    def _thread_main(self):
        try:
            asyncio.run(self._capture_loop())
        except Exception as e:
            self.last_error = e
            self._opened = False
            self._ready_event.set()

    async def _find_ir_source(self):
        groups = await MediaFrameSourceGroup.find_all_async()
        candidates = []

        for group in groups:
            source_infos = list(group.source_infos)

            for source_info in source_infos:
                is_target_ir = (
                    source_info.source_kind
                    == MediaFrameSourceKind.INFRARED
                    and self.device_id_contains
                    in source_info.id.upper()
                )

                if not is_target_ir:
                    continue

                # RGBとIRをまとめたグループを優先する
                has_target_rgb = any(
                    item.source_kind
                    == MediaFrameSourceKind.COLOR
                    and self.device_id_contains
                    in item.id.upper()
                    for item in source_infos
                )

                candidates.append((has_target_rgb, group, source_info))

        if not candidates:
            raise RuntimeError("USBカメラのIRないよーーー；；")
        
        _, group, source_info = max(candidates, key = lambda item: item[0])

        return group, source_info
    
    async def _capture_loop(self):
        capture = None
        reader = None

        try:
            group, source_info = await self._find_ir_source()

            self.group_name = group.display_name
            self.source_id = source_info.id

            settings = MediaCaptureInitializationSettings()
            settings.source_group = group
            settings.sharing_mode = (MediaCaptureSharingMode.SHARED_READ_ONLY)
            settings.memory_preference = (MediaCaptureMemoryPreference.CPU)
            settings.streaming_capture_mode = (StreamingCaptureMode.VIDEO)

            capture = MediaCapture()
            await capture.initialize_with_settings_async(settings)
            
            ir_source = capture.frame_sources[source_info.id]
            reader = await capture.create_frame_reader_async(ir_source)

            status = await reader.start_async()

            if status != MediaFrameReaderStartStatus.SUCCESS:
                raise RuntimeError(f"IRreaderないよーーー {status}")
            
            self._opened = True
            self._ready_event.set()

            while not self._stop_event.is_set():
                reference = reader.try_acquire_latest_frame()

                if reference is None:
                    await asyncio.sleep(0.005)
                    continue

                try:
                    video_frame = reference.video_media_frame
                    bitmap = video_frame.software_bitmap

                    if bitmap is None:
                        continue

                    if bitmap.bitmap_pixel_format != BitmapPixelFormat.GRAY8:
                        raise RuntimeError(f"IR画像がGRAY8じゃない {bitmap.bitmap_pixel_format}")
                    
                    width = bitmap.pixel_width
                    height = bitmap.pixel_height

                    buffer = Buffer(width * height)
                    bitmap.copy_to_buffer(buffer)

                    frame = np.frombuffer(memoryview(buffer), dtype = np.uint8, count = width * height).reshape(height, width).copy()

                    with self._lock:
                        self._latest_frame = frame
                        self._latest_at = time.monotonic()
                    
                finally:
                    reference.close()
        
        finally:
            self._opened = False
            self._ready_event.set()

            if reader is not None:
                try:
                    await reader.stop_async()
                except Exception:
                    pass

                reader.close()

            if capture is not None:
                capture.close()