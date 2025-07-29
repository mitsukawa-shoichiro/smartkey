@echo off
rem install.bat  ─ 任何路径下双击即可

rem ① 切到当前批处理文件所在目录
pushd "%~dp0"

rem ② 升级 pip（可选）
python -m pip install --upgrade pip

rem ③ 安装依赖（全局 or --user 安装）
python -m pip install -r requirements.txt --user

rem ④ 返回原工作目录
popd