# JNUAutoElective

English | [中文说明](README.zh-CN.md)

JNUAutoElective is a local helper for the Jinan University course selection system. It runs on your own computer, opens a local web dashboard, captures the session created by your normal browser login, lets you search and confirm teaching classes, and submits only the classes you explicitly add to the target list.

This project does not include or commit any user credentials. Login credentials are generated only on your own computer, saved by default as `credentials.json`, and excluded from version control by `.gitignore`. Do not share `credentials.json` with anyone, and do not upload it to public repositories, cloud drives, screenshots, or chat groups.

> For learning, communication, and automation research only. Follow your university's course selection rules, system policies, and request-rate limits. You are responsible for any consequences of using this tool.

## Contents

- [Quick start](#quick-start)
- [Recommended web dashboard workflow](#recommended-web-dashboard-workflow)
- [Timetable page](#timetable-page)
- [Command-line mode](#command-line-mode)
- [FAQ and troubleshooting](#faq-and-troubleshooting)
- [Security and compliance checklist](#security-and-compliance-checklist)
- [Project structure](#project-structure)
- [中文说明](README.zh-CN.md)

## What it does

| Area | Current behavior |
| --- | --- |
| Local start | On Windows, double-click `start_web.bat` to create `.venv`, install dependencies, start the local service, and open the dashboard. |
| Login capture | Opens Chrome first, then Edge if needed. It listens for the target course-selection request and saves local credentials. |
| Course search | Accepts one teaching class ID or course name per line. Course-name searches may return multiple candidate teaching classes. |
| Explicit target list | Search results are not submitted automatically. Only checked classes added to the target list enter the submission loop. |
| Timed submission | Interprets the official start time in `Asia/Shanghai`, optionally starts early by a configured number of seconds, and submits repeatedly. |
| Stop behavior | Stops when the response is judged successful on a best-effort basis, or when you manually stop it. |
| Logs | Shows login, search, scheduling, per-round submission, and error messages. |
| Timetable | Shows Monday-Sunday and periods 1-13. Courses with parseable time fields are placed into the grid. |

## Quick start

Requirements:

- Windows
- Python 3.9 or later
- Chrome or Edge
- Network access to the Jinan University course selection system
- A valid school account and current course-selection eligibility

Run:

```text
start_web.bat
```

The script starts the local dashboard and usually opens:

```text
http://127.0.0.1:8765/
```

If the browser does not open automatically, keep the black terminal window running and visit the URL manually.

First startup may take longer because the script creates a virtual environment and installs dependencies. Do not close the black terminal window while using the dashboard; it is the local service process.

## Recommended web dashboard workflow

### 1. Start the dashboard

Double-click `start_web.bat` in the project root.

The start page shows Beijing time. Click `Start` to enter the dashboard.

### 2. Log in and capture local credentials

If the dashboard shows that you are not logged in, the program opens Chrome or Edge.

The `Get credentials` page is the university's normal login page. You may log in with a QR code or with your account and password.

After a successful login, the program waits for the course-selection request, saves `credentials.json` locally, closes the login window, and changes the dashboard status to logged in.

Important:

- `credentials.json` contains sensitive local session information.
- Do not share it with anyone.
- Do not upload it to GitHub, cloud drives, screenshots, or chat groups.
- If the session expires, the course-selection batch changes, or you log in again, old credentials may stop working. Use `Reopen login` or `Relogin` to capture fresh credentials.
- The default capture wait time is 120 seconds.

### 3. Search candidate courses

In the course search box, enter one teaching class ID or course name per line, then click `Search`.

The candidate area shows available information such as course name, teaching class ID, instructor, department, time, and location.

Course names may match multiple teaching classes. Check the instructor, campus, time, location, and teaching class ID carefully. Do not confuse the course ID with the teaching class ID.

### 4. Build the target list

Check the exact candidate teaching classes you want, then click `Add to target list`.

Before starting, review the target list on the left. You can remove individual items or clear the whole list.

Only the target list is submitted. Candidate results are for discovery and confirmation only.

### 5. Set time and frequency

| Setting | Meaning |
| --- | --- |
| Official start time | Interpreted as Beijing time (`Asia/Shanghai`). Change the example to the real start time for your selection round. |
| Early-access seconds | Actual start time = official start time minus this many seconds. Default is 60 seconds. |
| Submit interval seconds | Waiting time between requests or rounds. The backend accepts a minimum of 0.02 seconds. |

If the calculated start time is already in the past, the task starts immediately.

Higher frequency does not guarantee success and may trigger rate limits or violate system rules. Use a careful, compliant interval.

### 6. Start, observe, and stop

When you click `Start selection`, the program:

1. Freezes a copy of the current target list.
2. Waits until `official start time - early-access seconds`.
3. Submits each target class in order.
4. Repeats the next round.
5. Records success and stops when the response is judged successful on a best-effort basis.
6. Lets you stop manually at any time.

Use the running log as the first place to troubleshoot. Always verify the final result in the official university system; do not rely only on the script's text judgment.

## Timetable page

Click `Schedule` in the top-right corner to open the timetable page.

The page shows Monday-Sunday and periods 1-13. It uses courses already queried in the dashboard, so it is not a complete official personal timetable.

Only courses whose returned time fields can be parsed into weekday and period information are placed into the grid. Use the top-left return button to go back to the dashboard.

## Command-line mode

Command-line mode is intended for debugging, dry runs, and reproducible batch submission.

### Manual installation

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Capture credentials

```bash
python -m jnu_auto_elective capture --out credentials.json
```

Log in normally in the browser. QR-code login and account/password login are both supported.

After capture succeeds, the program saves fields such as the student code, elective batch code, Cookie, Token, and User-Agent into `credentials.json`.

### Prepare `classes.txt`

Create `classes.txt`, one teaching class ID per line. Empty lines and lines beginning with `#` are ignored.

```txt
# one teaching class ID per line
ABC123-01
DEF456-02
```

### Dry run, then submit

Query only:

```bash
python -m jnu_auto_elective run --credentials credentials.json --classes classes.txt --dry-run
```

Submit:

```bash
python -m jnu_auto_elective run --credentials credentials.json --classes classes.txt --rounds 3 --interval 1
```

Options:

- `--dry-run`: query only, without submitting.
- `--rounds`: number of repeated submission rounds, default `3`.
- `--interval`: interval in seconds between requests, default `1.0`.

Unlike the web dashboard, command-line `run` ends after the specified number of rounds. It does not provide the dashboard's scheduled waiting and continuous monitoring interface.

You can also start the web service directly:

```bash
python -m jnu_auto_elective web
python -m jnu_auto_elective web --no-open
```

## FAQ and troubleshooting

| Problem | What to try |
| --- | --- |
| Double-click says Python cannot be found | Install Python 3.9+, confirm `python --version` works in a terminal, then run again. |
| Browser does not open automatically | Keep the black terminal window running and manually visit `http://127.0.0.1:8765/`. |
| Chrome or Edge cannot start | Confirm at least one supported browser is installed; check logs for driver or browser startup errors. |
| Dashboard stays not logged in | Complete normal login in the popup window and trigger the course-selection page request. If it times out, click relogin. |
| Search returns nothing | Check the teaching class ID or course name, current batch, login status, and network. Course-name search can only read candidates returned by the current interface. |
| Start button is disabled | Confirm you are logged in, no task is already running, and the target list is not empty. |
| Task starts immediately | `official start time - early-access seconds` is already in the past. Check date, time, and early-access setting. |
| Script says success but official system does not | Success detection is based on response text and is best effort. The official university system is authoritative. |
| Timetable misses courses | Query courses in the dashboard first. If returned time fields cannot be parsed, the course cannot be placed into the grid automatically. |

## Security and compliance checklist

- Run it only on your own computer.
- Confirm the dashboard address is local: `127.0.0.1`.
- Do not share or upload `credentials.json`.
- Do not use real credentials in screenshots or demos.
- Before starting, verify teaching class IDs, instructors, time, location, and the target list.
- Use request frequencies allowed by the university system.
- Stop immediately if you see rate limits, abnormal behavior, or rule warnings.
- Treat the official university system as the final source of truth.
- Close the service window after use.

## Project structure

```text
jnu_auto_elective/
  __main__.py       module entry point
  cli.py            CLI arguments and workflow orchestration
  client.py         course selection API wrapper
  config.py         URLs and default options
  credentials.py    credential parsing, saving, and loading
  sniffer.py        selenium-wire login request capture
  web.py            local web dashboard
```

