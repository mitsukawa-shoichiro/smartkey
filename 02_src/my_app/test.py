import sys
import os

# 02_src をパスに追加
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from my_app.service.backsys.opensensor_back_system import main

if __name__ == "__main__":
    main()