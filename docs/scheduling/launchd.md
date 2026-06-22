# macOS launchd Scheduling

Use launchd when this repository should run on a Mac without depending on an agent harness. Configure the job to run `frontier-radar daily` from `/Users/xwli/Documents/st` at 8:00 AM in the machine timezone, with the machine timezone set to America/Los_Angeles if Pacific time behavior is required.

Example `~/Library/LaunchAgents/com.local.frontier-radar.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.local.frontier-radar</string>
  <key>WorkingDirectory</key>
  <string>/Users/xwli/Documents/st</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/xwli/Documents/st/.venv/bin/frontier-radar</string>
    <string>daily</string>
    <string>--budget-minutes</string>
    <string>20</string>
    <string>--top-n</string>
    <string>30</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>8</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/xwli/Documents/st/state/frontier-radar.launchd.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/xwli/Documents/st/state/frontier-radar.launchd.err</string>
</dict>
</plist>
```

launchd uses the Mac's configured timezone. Keep the machine timezone on Pacific time if daylight-saving-aware 8:00 AM Pacific behavior is required.

Create separate launchd jobs for purpose-specific follow-up work instead of scheduling `fetch`, `rank`, and `digest` separately:

```bash
/Users/xwli/Documents/st/.venv/bin/frontier-radar retry-failed --since today --budget-minutes 10
/Users/xwli/Documents/st/.venv/bin/frontier-radar enrich --since 7d --budget-minutes 60 --top-n 100
/Users/xwli/Documents/st/.venv/bin/frontier-radar health
```
