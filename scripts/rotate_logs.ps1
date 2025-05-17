# Log Rotation and Monitoring Script
# This script handles log rotation and monitoring for Railway deployment logs

param(
    [string]$LogsPath = ".\logs",
    [string]$ArchivePath = ".\logs\archive",
    [int]$MaxStorageGB = 10,
    [int]$AlertThresholdGB = 8
)

# Function to get directory size in GB
function Get-DirectorySize {
    param([string]$Path)
    $size = (Get-ChildItem -Path $Path -Recurse | Measure-Object -Property Length -Sum).Sum
    return [math]::Round($size / 1GB, 2)
}

# Function to send alert
function Send-StorageAlert {
    param(
        [string]$Message,
        [string]$Severity = "Warning"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $alertMessage = "[$timestamp] [$Severity] $Message"
    
    # Write to alert log
    Add-Content -Path "$LogsPath\storage_alerts.log" -Value $alertMessage
    
    # TODO: Implement your preferred alerting method (email, Slack, etc.)
    Write-Host $alertMessage
}

# Check storage usage
$currentSize = Get-DirectorySize -Path $LogsPath
if ($currentSize -ge $MaxStorageGB) {
    Send-StorageAlert -Message "CRITICAL: Log storage has reached maximum capacity ($currentSize GB)" -Severity "Critical"
    exit 1
}
elseif ($currentSize -ge $AlertThresholdGB) {
    Send-StorageAlert -Message "WARNING: Log storage is approaching maximum capacity ($currentSize GB)"
}

# Get current date
$currentDate = Get-Date
$thirtyDaysAgo = $currentDate.AddDays(-30)
$ninetyDaysAgo = $currentDate.AddDays(-90)

# Process logs older than 30 days
Get-ChildItem -Path "$LogsPath\*.log" | ForEach-Object {
    if ($_.LastWriteTime -lt $thirtyDaysAgo) {
        # Create monthly archive directory if it doesn't exist
        $archiveMonth = $_.LastWriteTime.ToString("yyyy-MM")
        $monthlyArchivePath = "$ArchivePath\$archiveMonth"
        if (-not (Test-Path $monthlyArchivePath)) {
            New-Item -ItemType Directory -Path $monthlyArchivePath | Out-Null
        }
        
        # Move file to archive
        Move-Item -Path $_.FullName -Destination "$monthlyArchivePath\$($_.Name)"
    }
}

# Process archives older than 90 days
Get-ChildItem -Path $ArchivePath -Directory | ForEach-Object {
    if ($_.LastWriteTime -lt $ninetyDaysAgo) {
        # Create zip archive
        $archiveName = "$ArchivePath\$($_.Name)_archive.zip"
        if (-not (Test-Path $archiveName)) {
            Compress-Archive -Path $_.FullName -DestinationPath $archiveName
            # Remove original directory after successful compression
            Remove-Item -Path $_.FullName -Recurse -Force
        }
    }
}

# Clean up old zip archives (optional - uncomment if needed)
# Get-ChildItem -Path "$ArchivePath\*.zip" | ForEach-Object {
#     if ($_.LastWriteTime -lt $ninetyDaysAgo) {
#         Remove-Item -Path $_.FullName -Force
#     }
# }

# Log rotation complete
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path "$LogsPath\rotation.log" -Value "[$timestamp] Log rotation completed successfully" 