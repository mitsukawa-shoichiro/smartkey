import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

repo = Path(r"C:\smartkey\02_src\my_app\vendor\Silent-Face-Anti-Spoofing")

print("=== 直下 ===")
for p in sorted(repo.iterdir()):
    print(("[dir] " if p.is_dir() else "[file]") + " " + p.name)

print("\n=== .onnx を全部探す ===")
for p in sorted(repo.rglob("*.onnx")):
    print(p)

print("\n=== resources の中身(あれば) ===")
res = repo / "resources"
if res.is_dir():
    for p in sorted(res.rglob("*")):
        print(p.relative_to(repo))
else:
    print("resources フォルダ自体がない")