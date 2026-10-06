# Network Health Monitor

A Python tool that checks whether network devices are reachable using ping
and TCP port tests, then logs the results to CSV. Built to give small
organisations early warning of outages without paid monitoring software.

## Features
- Ping and TCP port checks for a list of devices in `devices.json`
- Three statuses: **UP**, **DEGRADED** (ping works but the service port
  is closed) and **DOWN**
- Response time measurement and timestamped CSV log
- Exit code 1 when any device is down, so it can be used in scripts and cron

## Tools
Python 3.8, standard library only (socket, subprocess, csv, json), Linux, Git

## How to run
git clone https://github.com/fortunemwinzi/network-health-monitor.git
cd network-health-monitor
python3 monitor.py

Edit `devices.json` to add your own devices:
{"name": "Office Router", "host": "192.168.1.1", "port": 80}

## Sample output
DEVICE                    HOST            STATUS    LATENCY
Loopback                  127.0.0.1       UP        -
Google DNS                8.8.8.8         UP        60.6 ms
Cloudflare DNS            1.1.1.1         UP        189.3 ms
Closed Port Test          127.0.0.1       DEGRADED  -
Unused Local Address      10.0.2.99       DOWN      -

4/5 devices up

## What I learned
- During testing, 192.0.2.1 (a reserved test address) showed as UP because
  my lab network answered for it. I then split the status into UP,
  DEGRADED and DOWN and used predictable local test targets.
- The python's socket and subprocess modules allowed me to test a service port and run ping without extra libraries.
- My first version marked a device UP if either check passed, which hid partial failures, so I added a DEGRADED status.
- I used Git branches and resolved a merge conflict when my local repo and GitHub's starter files disagreed.

## Roadmap
- [X] HTML report
- [ ] Email or Telegram alerts when a device goes down
- [ ] Scheduled runs with cron
## Scheduling

The monitor runs every 5 minutes using cron. A small wrapper script
(`run_monitor.sh`) loads the Telegram credentials from a private file in
the home folder, which is kept outside the repository, then runs the check
and appends the output to `logs/cron.log`.

1. Create `~/.monitor_env` (never commit this file):
```
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"
```
2. Restrict access to it: `chmod 600 ~/.monitor_env`
3. Make the wrapper executable: `chmod +x run_monitor.sh`
4. Open the cron editor with `crontab -e` and add:
```
*/5 * * * * /home/devasc/network-health-monitor/run_monitor.sh
```

Alerts are sent to Telegram only when a device changes status
(for example UP -> DOWN), so a persistent fault doesn't send a message
every 5 minutes.

### Limitations
Tested in a Linux VM, so cron only runs while the VM is on. A real
deployment would run on an always-on machine such as a small server
or Raspberry Pi.
