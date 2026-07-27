import argparse
from pathlib import Path

# face_core.py から読み込み
from face_core import (
    REGISTER_IMAGE_DIR,
    REGISTERED_FACE_PATH,
    register_faces,
)

def main():
    registered_count = register_faces(
        image_dir=REGISTER_IMAGE_DIR,
        output_path=REGISTERED_FACE_PATH,
    )

    if registered_count > 0:
        print(f"登録数: [registered_count]")



if __name__ == "__main__":
    main()