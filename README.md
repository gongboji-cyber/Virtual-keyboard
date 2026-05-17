# GMU25mr_gong-模拟键盘

一个基于 Python + PyQt5 的 Windows 模拟键盘输入小工具。
直接下载使用（百度网盘）：https://pan.baidu.com/s/5jg2jCorCV_hppulvMfWwQg

## 功能

- 图形化文本输入界面
- 可调输入速度
- 开始倒计时
- 暂停 / 继续 / 停止
- 窗口置顶
- Windows EXE 打包
- 自定义医学风格图标

## 本地运行

```powershell
cd "D:\GMU25mr_gong_keyboard"

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## 打包为 EXE

```powershell
cd "D:\GMU25mr_gong_keyboard"
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

打包结果：

```text
dist\GMU25mr_gong-模拟键盘.exe
```

## GitHub Actions 自动构建

推送到 GitHub 后，可在仓库的 **Actions** 页面运行 `Build Windows EXE` 工作流，构建完成后从 Artifacts 下载 Windows exe。

## 注意

本工具使用 Windows 用户态输入模拟，不是硬件 HID 键盘。部分管理员权限窗口、受保护窗口、游戏或反作弊环境可能不支持。
