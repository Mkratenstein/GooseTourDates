# Log Rotation and Monitoring Script
# This script handles log rotation and monitoring for Railway deployment logs and Discord bot logs

param(
    [string]$LogsPath = ".\logs",
    [string]$ArchivePath = ".\logs\archive",
    [int]$MaxStorageGB = 10,
    [int]$AlertThresholdGB = 8
)

# Ensure required directories exist
if (-not (Test-Path $LogsPath)) {
    New-Item -ItemType Directory -Path $LogsPath | Out-Null
    Write-Host "Created logs directory: $LogsPath"
}

if (-not (Test-Path $ArchivePath)) {
    New-Item -ItemType Directory -Path $ArchivePath | Out-Null
    Write-Host "Created archive directory: $ArchivePath"
}

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
$threeSixtyFiveDaysAgo = $currentDate.AddDays(-365)

# Process all log files (including Discord bot logs)
$logPatterns = @(
    "*.log",                    # All log files
    "discord_bot*.log",         # Discord bot logs
    "discord_bot*.log.*"        # Discord bot rotated logs
)

foreach ($pattern in $logPatterns) {
    Get-ChildItem -Path "$LogsPath\$pattern" | ForEach-Object {
        if ($_.LastWriteTime -lt $thirtyDaysAgo) {
            # Create monthly archive directory if it doesn't exist
            $archiveMonth = $_.LastWriteTime.ToString("yyyy-MM")
            $monthlyArchivePath = "$ArchivePath\$archiveMonth"
            if (-not (Test-Path $monthlyArchivePath)) {
                New-Item -ItemType Directory -Path $monthlyArchivePath | Out-Null
            }
            
            # Move file to archive
            try {
                Move-Item -Path $_.FullName -Destination "$monthlyArchivePath\$($_.Name)" -Force
                Write-Host "Moved $($_.Name) to $monthlyArchivePath"
            }
            catch {
                Write-Host "Failed to move $($_.Name): $_"
            }
        }
    }
}

# Process archives older than 90 days
Get-ChildItem -Path $ArchivePath -Directory | ForEach-Object {
    if ($_.LastWriteTime -lt $ninetyDaysAgo) {
        # Create zip archive
        $archiveName = "$ArchivePath\$($_.Name)_archive.zip"
        if (-not (Test-Path $archiveName)) {
            try {
                Compress-Archive -Path $_.FullName -DestinationPath $archiveName
                # Remove original directory after successful compression
                Remove-Item -Path $_.FullName -Recurse -Force
                Write-Host "Compressed and removed $($_.Name) to $archiveName"
            }
            catch {
                Write-Host "Failed to compress $($_.Name): $_"
            }
        }
    }
}

# Delete compressed archives older than 365 days
Get-ChildItem -Path "$ArchivePath\*.zip" | ForEach-Object {
    if ($_.LastWriteTime -lt $threeSixtyFiveDaysAgo) {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $logMsg = "[$timestamp] Deleted archive: $($_.FullName) (LastWriteTime: $($_.LastWriteTime)) (older than 365 days)"
        try {
            Remove-Item -Path $_.FullName -Force
            Add-Content -Path "$LogsPath\rotation.log" -Value $logMsg
            Write-Host "Deleted old archive: $($_.Name)"
        }
        catch {
            Write-Host "Failed to delete $($_.Name): $_"
        }
    }
}

# Log rotation complete
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path "$LogsPath\rotation.log" -Value "[$timestamp] Log rotation completed successfully"
Write-Host "Log rotation completed successfully at $timestamp" 