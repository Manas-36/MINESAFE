@echo off
REM MineSafe admin hub - double-click this file (or run it from a terminal).
cd /d "%~dp0"
echo Installing / checking Flask ...
python -m pip install -q -r requirements.txt
echo.
echo Laptop IP addresses (use the Wi-Fi one, NOT 192.168.56.x = VirtualBox):
ipconfig | findstr /C:"IPv4"
echo.
echo Admin page:  http://localhost:5000      Phone:  http://^<Wi-Fi IP^>:5000/phone
echo Press Ctrl+C to stop.
python admin_hub.py
pause
