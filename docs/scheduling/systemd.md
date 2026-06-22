# systemd Timer Scheduling

Use a user-level systemd timer on Linux. The service should run `frontier-radar daily` from `/Users/xwli/Documents/st`. Configure the timer for 8:00 AM in the desired local timezone.

Example `~/.config/systemd/user/frontier-radar.service`:

```ini
[Unit]
Description=Frontier Radar daily digest

[Service]
Type=oneshot
WorkingDirectory=/Users/xwli/Documents/st
ExecStart=/Users/xwli/Documents/st/.venv/bin/frontier-radar daily --budget-minutes 20 --top-n 30
```

Example `~/.config/systemd/user/frontier-radar.timer`:

```ini
[Unit]
Description=Run Frontier Radar at 8 AM Pacific

[Timer]
OnCalendar=*-*-* 08:00:00 America/Los_Angeles
Persistent=true

[Install]
WantedBy=timers.target
```

Enable with:

```bash
systemctl --user daemon-reload
systemctl --user enable --now frontier-radar.timer
```

Use separate services/timers for reliability jobs:

```ini
ExecStart=/Users/xwli/Documents/st/.venv/bin/frontier-radar retry-failed --since today --budget-minutes 10
ExecStart=/Users/xwli/Documents/st/.venv/bin/frontier-radar enrich --since 7d --budget-minutes 60 --top-n 100
ExecStart=/Users/xwli/Documents/st/.venv/bin/frontier-radar health
```

Keep `fetch`, `rank`, and `digest` as manual helper commands. The scheduled jobs should remain purpose-specific so state, locks, and checkpoints stay coordinated.
