@echo off
echo Packaging AlarmManager...
pyinstaller --noconsole --onefile --add-data "icon.png;." --name "AlarmManager" alarm_manager.pyw
echo Package completed! The executable is in the dist folder.
pause
