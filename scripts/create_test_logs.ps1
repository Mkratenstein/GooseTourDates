# Script to create test log files with different dates
$logsPath = ".\logs"
$archivePath = ".\logs\archive"

# Create test logs with different dates
$dates = @(
    (Get-Date).AddDays(-5),    # Recent log
    (Get-Date).AddDays(-35),   # Should be moved to archive
    (Get-Date).AddDays(-95)    # Should be compressed
)

foreach ($date in $dates) {
    $logName = $date.ToString("yyyy-MM-dd") + "_deployment.log"
    $logPath = Join-Path $logsPath $logName
    
    # Create log file with some content
    $content = @"
Test log file created on $($date.ToString("yyyy-MM-dd"))
This is a test deployment log.
"@
    
    Set-Content -Path $logPath -Value $content
    
    # Set the file's last write time to the specified date
    (Get-Item $logPath).LastWriteTime = $date
}

# Create a test archive file older than 365 days
$oldArchiveDate = (Get-Date).AddDays(-370)
$oldArchiveName = "2023-01_archive.zip"
$oldArchivePath = Join-Path $archivePath $oldArchiveName

# Ensure archive directory exists
if (-not (Test-Path $archivePath)) {
    New-Item -ItemType Directory -Path $archivePath | Out-Null
}

# Create a dummy zip file
Set-Content -Path $oldArchivePath -Value "Dummy archive content"
# Set the file's last write time to over 365 days ago
(Get-Item $oldArchivePath).LastWriteTime = $oldArchiveDate

Write-Host "Test log files and old archive have been created:"
Get-ChildItem -Path $logsPath -Filter "*.log" | ForEach-Object {
    Write-Host "  $($_.Name) (Last Write: $($_.LastWriteTime))"
}
Get-ChildItem -Path $archivePath -Filter "*.zip" | ForEach-Object {
    Write-Host "  $($_.Name) (Last Write: $($_.LastWriteTime))"
} 