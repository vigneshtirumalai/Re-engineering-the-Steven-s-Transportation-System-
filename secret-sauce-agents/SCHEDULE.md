# Scheduling the 06:00 run

`scripts/run_morning.sh` runs `claude -p "/morning"` headless with
`config/headless-settings.json`, logs to `logs/runs/<date>.log`, and always leaves
`outputs/brief/<date>.md` (a FAILED brief if anything went wrong). Nothing here is
installed automatically. Pick your OS, replace `REPO_PATH`, and run the commands yourself.

Before scheduling, check once by hand: `bash scripts/run_morning.sh; echo $?` and open
today's brief. Claude Code must be logged in on that machine, and `.env` must point
`SECRET_SAUCE_INBOX` at the Google Drive for desktop folder. If the inbox is outside the
repo, add it to `additionalDirectories` in `config/headless-settings.json` so the agents
can read it.

## macOS (launchd + scheduled wake)

The Mac must be in Asia/Kolkata time (launchd uses local time).

Install:
```sh
sed "s|REPO_PATH|$PWD|g" config/schedule/com.secretsauce.morning.plist > ~/Library/LaunchAgents/com.secretsauce.morning.plist
launchctl load ~/Library/LaunchAgents/com.secretsauce.morning.plist
sudo pmset repeat wakeorpoweron MTWRFSU 05:55:00
```

Uninstall:
```sh
launchctl unload ~/Library/LaunchAgents/com.secretsauce.morning.plist
rm ~/Library/LaunchAgents/com.secretsauce.morning.plist
sudo pmset repeat cancel
```

When the wake will not fire: a MacBook with the lid closed and no external display,
or on battery, often stays asleep. Keep it on power with the lid open, or use a desktop.
`pmset repeat` holds one schedule; `cancel` also removes any other repeat you had set.

## Linux (cron)

Install: `(crontab -l 2>/dev/null; sed "s|REPO_PATH|$PWD|g" config/schedule/crontab.txt) | crontab -`

Uninstall: `crontab -l | grep -v run_morning.sh | grep -v '^CRON_TZ=Asia/Kolkata' | crontab -`

cron cannot wake a sleeping machine; keep it on, or set a wake alarm with `rtcwake`.

## Windows (Task Scheduler)

Run in PowerShell from the repo folder (needs Git Bash or WSL for the shell script):
```powershell
$action  = New-ScheduledTaskAction -Execute "C:\Program Files\Git\bin\bash.exe" -Argument "`"$PWD\scripts\run_morning.sh`""
$trigger = New-ScheduledTaskTrigger -Daily -At 6:00am
$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable
Register-ScheduledTask -TaskName "SecretSauceMorning" -Action $action -Trigger $trigger -Settings $settings
```
The PC must be in India Standard Time. "Wake timers" must be enabled in the power plan.

Uninstall: `Unregister-ScheduledTask -TaskName "SecretSauceMorning" -Confirm:$false`
