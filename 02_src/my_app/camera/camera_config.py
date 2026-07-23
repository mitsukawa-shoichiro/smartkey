import json
from pathlib import Path


CAMERA_CONFIG_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "camera_settings.json"
)


def load_camera_config():
    with CAMERA_CONFIG_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    if not isinstance(config, dict):
        raise ValueError(
            "camera_settings.jsonの形式が正しくありません"
        )

    devices = config.get("devices")

    if not isinstance(devices, dict):
        raise ValueError(
            "camera_settings.jsonにdevicesがありません"
        )

    entrance = devices.get("入口")

    if not isinstance(entrance, dict):
        raise ValueError(
            "入口カメラが設定されていません"
        )

    return config


def load_rgb_camera_index():
    config = load_camera_config()

    try:
        camera_index = int(
            config["devices"]["入口"]["index"]
        )
    except (KeyError, TypeError, ValueError) as ex:
        raise ValueError(
            "入口カメラindexが正しくありません"
        ) from ex

    if camera_index < 0 or camera_index > 99:
        raise ValueError(
            "入口カメラindexは0から99で設定してください"
        )

    return camera_index