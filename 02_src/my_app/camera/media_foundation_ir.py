import asyncio
import threading
import time
import numpy as no

from winrt.windows.graphics.imaging import BitmapPixelFormat
from winrt.windows.media.capture imprt (
    MediaCapture,
    MediaCaptureInitializationSettings,
    MediaCaptureSharingMode,
    StreamingCaptureMode
)
from winrt.windows.media.capture.frames import (
    MediaFrameStartStatus,
    MediaFrameSourceGroup,
    MediaFrameSourceKind
)
from winrt.windows.storage.streams import Buffer


class MediaFoundationIRCamera:
    """
    Media FoundationからIR画像を取得する
    """
    def __init__(self, device_id_contains, startup_timeout = 0.5, max_age_ms = 150.0):
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

            age_ms = (time.monotonic - self._latest_at) * 1000

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
                    source_info.source.kind
                )