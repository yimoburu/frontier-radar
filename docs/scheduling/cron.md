# Cron Scheduling

Run Frontier Radar daily through the plain CLI command:

```bash
frontier-radar daily
```

Use the machine's timezone or set `TZ=America/Los_Angeles` in the crontab environment before the schedule entry.

Example crontab entry:

```cron
TZ=America/Los_Angeles
0 8 * * * cd /Users/xwli/Documents/st && /Users/xwli/Documents/st/.venv/bin/frontier-radar daily >> /Users/xwli/Documents/st/state/frontier-radar.cron.log 2>&1
```

If the package is installed on the system `PATH`, `frontier-radar daily` can replace the explicit `.venv` command.
