import os
import time
import datetime
import logging

# 配置日志，以便你可以追踪重启事件和错误
logging.basicConfig(filename='reboot.log', level=logging.INFO,
                    format='%(asctime)s - %(message)s')

def reboot_computer_at_time(reboot_time_str):
    """
    计算并等待到指定时间，然后重启系统。

    参数:
    reboot_time_str (str): 每天重启的时间，格式为 "HH:MM"。
    """
    try:
        # 解析输入的重启时间字符串
        reboot_hour, reboot_minute = map(int, reboot_time_str.split(':'))
        
    except ValueError:
        logging.error(f"Invalid time format: {reboot_time_str}. Please use HH:MM format.")
        return

    while True:
        # 获取当前时间
        now = datetime.datetime.now()
        
        # 构建今天和明天的重启时间点
        reboot_time_today = now.replace(hour=reboot_hour, minute=reboot_minute, second=0, microsecond=0)

        # 检查重启时间是否在今天
        if now < reboot_time_today:
            # 如果还没到今天设定的重启时间，就等待到今天的时间点
            wait_seconds = (reboot_time_today - now).total_seconds()
        else:
            # 如果今天已经过了重启时间，就等待到明天的时间点
            reboot_time_tomorrow = reboot_time_today + datetime.timedelta(days=1)
            wait_seconds = (reboot_time_tomorrow - now).total_seconds()
        
        logging.info(f"Current time is {now}. Waiting for {wait_seconds} seconds until {reboot_time_today if now < reboot_time_today else reboot_time_tomorrow}.")

        # 等待到指定时间
        time.sleep(wait_seconds)

        # 到达指定时间后，执行重启
        logging.info("Scheduled time reached. Initiating system reboot.")
        os.system("shutdown /r /t 0")

if __name__ == "__main__":
    # 在这里指定你想要的重启时间，例如 "00:00"
    reboot_computer_at_time("14:49")