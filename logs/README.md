# Deployment Logs

This directory contains deployment logs from Railway deployments.

## Purpose

- Store deployment logs for reference and debugging
- Track deployment history
- Monitor application performance and issues

## Log File Naming Convention

Log files should follow this naming convention:
```
YYYY-MM-DD_deployment.log
```

Example: `2024-03-20_deployment.log`

## Important Notes

- Log files are automatically ignored by git (see root .gitignore)
- Keep logs for at least 30 days for debugging purposes
- Do not commit sensitive information in logs
- Rotate logs periodically to manage disk space 