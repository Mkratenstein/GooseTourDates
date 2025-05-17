# Script to set up the scheduled task for log rotation
# Run this script as Administrator

$taskName = "GooseTourDates-LogRotation"
$taskDescription = "Rotates and monitors Railway deployment logs"
$scriptPath = Join-Path $PSScriptRoot "rotate_logs.ps1"

# Create the scheduled task action
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

# Create the trigger (weekly on Sunday at midnight)
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 12am

# Create the settings
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

# Register the scheduled task
Register-ScheduledTask -TaskName $taskName `
    -Description $taskDescription `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Force

Write-Host "Scheduled task '$taskName' has been created successfully."
Write-Host "The task will run weekly on Sunday at midnight." 