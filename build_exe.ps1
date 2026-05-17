$ErrorActionPreference = "Stop"

$AppName = "GMU25mr_gong-模拟键盘"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist) { Remove-Item dist -Recurse -Force }
if (Test-Path "$AppName.spec") { Remove-Item "$AppName.spec" -Force }

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name "$AppName" `
  --icon "assets\app.ico" `
  --add-data "assets\app.ico;assets" `
  --collect-all PyQt5 `
  main.py

Write-Host ""
Write-Host "打包完成：dist\$AppName.exe"
