# Log Rotation Policy

## Retention Periods

1. **Active Logs (Last 30 days)**
   - Keep all logs from the last 30 days
   - Store in the main `logs` directory
   - Format: `YYYY-MM-DD_deployment.log`

2. **Archive Logs (31-90 days)**
   - Move logs older than 30 days to `logs/archive/`
   - Compress these logs into monthly archives
   - Format: `YYYY-MM_archive.zip`

3. **Long-term Storage (90+ days)**
   - After 90 days, logs should be:
     - Reviewed for any critical information
     - Archived to long-term storage if needed
     - Deleted if no longer required

## Rotation Schedule

- **Daily**: New deployment logs are created as needed
- **Weekly**: Check for logs older than 30 days and move to archive
- **Monthly**: 
  - Compress archived logs into monthly archives
  - Review logs older than 90 days
  - Clean up unnecessary logs

## Archive Structure

```
logs/
├── 2024-03-20_deployment.log
├── 2024-03-21_deployment.log
├── archive/
│   ├── 2024-02_archive.zip
│   └── 2024-01_archive.zip
└── README.md
```

## Implementation Notes

1. **Automation**
   - Consider using a cron job or scheduled task for rotation
   - Example cron schedule: `0 0 * * 0` (weekly at midnight)

2. **Storage Management**
   - Monitor total log storage size
   - Set maximum storage limits
   - Alert when approaching limits

3. **Backup**
   - Keep a backup of archived logs
   - Consider cloud storage for long-term archives

4. **Security**
   - Ensure archived logs maintain proper access controls
   - Encrypt sensitive archived logs
   - Follow data retention policies 