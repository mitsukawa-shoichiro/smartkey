import logging
import win32serviceutil
import win32service
import win32event
import time

class MyPythonService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SimpleHelloService"
    _svc_display_name_ = "Simple Hello World Python Service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

    def SvcDoRun(self):
        while self.running:
            logging.info("Hello World")
            time.sleep(10)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.running = False
        win32event.SetEvent(self.hWaitStop)

if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(MyPythonService)