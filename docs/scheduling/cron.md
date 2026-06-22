# Cron Scheduling

Run Frontier Radar daily through the plain CLI command:

```bash
frontier-radar daily
```

Use the machine's timezone or set `TZ=America/Los_Angeles` in the crontab environment before the schedule entry.

Example crontab entry:

```cron
TZ=America/Los_Angeles
0 8 * * * cd /Users/xwli/Documents/st && /Users/xwli/Documents/st/.venv/bin/frontier-radar daily --budget-minutes 20 --top-n 30 >> /Users/xwli/Documents/st/state/frontier-radar.cron.log 2>&1
0 10 * * * cd /Users/xwli/Documents/st && /Users/xwli/Documents/st/.venv/bin/frontier-radar retry-failed --since today --budget-minutes 10 >> /Users/xwli/Documents/st/state/frontier-radar.retry.log 2>&1
0 9 * * 6 cd /Users/xwli/Documents/st && /Users/xwli/Documents/st/.venv/bin/frontier-radar enrich --since 7d --budget-minutes 60 --top-n 100 >> /Users/xwli/Documents/st/state/frontier-radar.enrich.log 2>&1
0 9 * * 0 cd /Users/xwli/Documents/st && /Users/xwli/Documents/st/.venv/bin/frontier-radar health >> /Users/xwli/Documents/st/state/frontier-radar.health.log 2>&1
```

If the package is installed on the system `PATH`, `frontier-radar daily` can replace the explicit `.venv` command.
