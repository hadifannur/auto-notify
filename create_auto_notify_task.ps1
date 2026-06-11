$action = New-ScheduledTaskAction -Execute "C:\Users\Admin\AppData\Local\Microsoft\WindowsApps\python.exe" -Argument "run.py" -WorkingDirectory "C:\Users\Admin\Desktop\auto-notify"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 4:00PM
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive
Register-ScheduledTask -TaskName "AutoNotify" -Action $action -Trigger $trigger -Principal $principal -Description "Run auto-notify run.py every weekday at 4pm" -Force
