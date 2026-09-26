@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   骑行轨迹地图 - 一键启动
echo ============================================
echo.
echo 正在启动图形界面，请稍候...
echo.
python gui.py
echo.
if errorlevel 1 (
  echo [失败] 生成出错，请确认电脑已安装 Python。
  echo 未安装可到 https://www.python.org/downloads/ 下载安装。
) else (
  echo 完成！地图已在浏览器打开。
)
echo.
pause
