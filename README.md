# JNUAutoElective

English | [中文说明](#中文说明)

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
- [中文说明](#中文说明)

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

For tests only:

```bash
pip install -r requirements-dev.txt
pytest
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
tests/
  test_client.py
  test_credentials.py
  test_web.py
```

## 中文说明

[返回英文](#jnuautoelective)

JNUAutoElective 是一个面向暨南大学选课系统的本地自动化工具，提供网页监控台和命令行两种使用方式。它可以捕获本地登录会话、查询教学班、维护待抢列表，并按设定时间提交选课请求。

项目不会内置或提交任何用户凭据。登录信息只会保存在你自己的电脑上，默认文件名为 `credentials.json`，并已被 `.gitignore` 排除在版本控制之外。请不要把 `credentials.json` 发给他人，也不要上传到公开仓库、网盘或聊天群。

### 点哪个运行？

Windows 用户直接双击项目根目录里的：

```text
start_web.bat
```

这个脚本会自动完成全部启动流程：创建项目自己的 `.venv` 虚拟环境、安装依赖、启动本地网页控制台，并打开：

```text
http://127.0.0.1:8765/
```

使用时保持 `start_web.bat` 打开的黑色窗口不要关闭。

### 推荐抢课流程

1. 抢课开始前约 5 分钟，双击 `start_web.bat`。
2. 启动页会显示北京时间大时钟，点击“开始”进入监控台。
3. 如果监控台显示未登录，程序会自动弹出 Chrome 或 Edge 登录窗口。
4. 弹出的“获取 credentials”页面就是学校系统的正常登录页面，可以用二维码登录，也可以用账号密码登录。
5. 登录成功后，程序会在本地生成或更新 `credentials.json`。这个文件相当于你的本地登录凭据，请自己保管，不要分享给他人。
6. 页面显示“已登录”后，输入要抢的教学班号；如果只知道课程名，也可以先用课程名查询。
7. 课程名查询可能返回多个教学班，请在候选列表里勾选真正要抢/选的教学班号。
8. 点击“加入待抢”，确认左侧“待抢列表”无误。
9. 设置“正式开抢时间（北京时间）”。
10. 设置“提前访问秒数”，默认提前 60 秒开始访问抢课接口。
11. 到抢课前点击“开始抢课”，程序会等到“正式开抢时间 - 提前访问秒数”再开始高频提交。
12. 程序只会针对待抢列表里的教学班号反复提交，直到判断选上或你手动点击“停止抢课”。

右上角“课表”按钮会打开独立课表页，展示一周七天、每天 1-13 节；课表页左上角可以返回主页面。

这个仓库走本地网页控制台和轻量命令行两条路线，方便阅读、测试和日常使用。

### 功能

- 自动打开 Chrome 或 Edge 登录选课系统并捕获必要凭据
- 支持二维码登录和账号密码登录
- 按“教学班号”查询课程信息
- 按课程名查询候选教学班
- 维护网页端待抢列表
- 按设定时间和提前访问秒数提交选课请求
- 按轮次批量提交选课请求
- 支持 `--dry-run` 只查询不提交
- 核心逻辑带单元测试，不依赖真实账号

### 环境

Python 3.9 及以上。

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

如果只跑测试：

```bash
pip install -r requirements-dev.txt
pytest
```

### 使用

#### 图形监控页面

推荐直接启动本地监控页面：

```bash
python -m jnu_auto_elective web
```

程序会用系统默认浏览器打开 `http://127.0.0.1:8765/` 启动页。点击“开始”进入监控台后，如果本地没有可用凭据，页面会自动请求后端弹出 Chrome 或 Edge 登录捕获窗口。这个获取 credentials 的页面就是学校系统的正常登录页面；你可以扫码登录，也可以使用账号密码登录。登录并捕获成功后，页面会进入监控状态。已有凭据时会直接进入监控页面。

页面里可以输入教学班号或课程名称、查询课程、查看授课教师/开课单位/上课时间地点，并查看实时日志。课程名查询可能返回多个候选教学班；请在候选列表里勾选真正要抢/选的教学班号，点击“加入待抢”，确认左侧待抢列表无误后再点击“开始抢课”。程序只会针对待抢列表里的教学班号反复提交，直到判断选上或你手动停止。右上角的“课表”按钮会打开独立课表页，展示一周七天、每天 1-13 节；左上角可返回主页面。如果教务返回的时间字段能解析出星期和节次，课程会自动落到对应格子里。

正式抢课建议提前约 5 分钟打开页面并完成登录，确认页面显示“已登录”后，再输入要抢的课程教学班号。到了抢课时间直接开始即可；如果只知道课程名称，先用课程名查询候选，再勾选对应教学班号。

#### 1. 捕获登录凭据

```bash
python -m jnu_auto_elective capture --out credentials.json
```

命令会启动 Chrome 或 Edge。请在浏览器里正常登录暨南大学选课系统，支持二维码登录或账号密码登录。程序监听到选课相关请求后会自动保存 `credentials.json`。

再次提醒：`credentials.json` 保存在本地，包含可以代表你当前登录状态的信息。不要把它分享给任何人，也不要提交到 Git 或公开平台。

#### 2. 准备教学班号

新建本地文件 `classes.txt`，每行一个教学班号：

```txt
ABC123-01
DEF456-02
```

注意：这里填的是“教学班号”，不是课程号。

#### 3. 先试跑查询

```bash
python -m jnu_auto_elective run --credentials credentials.json --classes classes.txt --dry-run
```

确认查询到的课程无误后，再执行提交。

#### 4. 开始提交

```bash
python -m jnu_auto_elective run --credentials credentials.json --classes classes.txt --rounds 3 --interval 1
```

参数说明：

- `--rounds`：对课程列表重复提交的轮数，默认 `3`
- `--interval`：每次请求之间的间隔秒数，默认 `1.0`
- `--dry-run`：只查询课程，不提交选课

### 项目结构

```text
jnu_auto_elective/
  __main__.py       模块入口
  cli.py            命令行参数与流程编排
  client.py         选课接口封装
  config.py         URL 与默认参数
  credentials.py    凭据解析、保存与读取
  sniffer.py        selenium-wire 登录请求捕获
tests/
  test_client.py
  test_credentials.py
```

### 最后

仅供学习、交流与自动化脚本研究，请遵守学校选课规定与系统使用规则。

使用本工具产生的任何后果由使用者自行承担。

### 常见问题与排查

| 现象 | 处理方法 |
| --- | --- |
| 双击后提示找不到 Python | 安装 Python 3.9+，确认命令行可运行 `python --version`，再重新启动。 |
| 浏览器没有自动打开 | 保持黑色窗口运行，手动访问 `http://127.0.0.1:8765/`。 |
| Chrome/Edge 无法启动 | 确认至少安装一种受支持浏览器；查看日志中的驱动或启动错误。 |
| 一直显示未登录 | 在弹出窗口内完成正常登录并触发选课页面请求；超时后点击重新登录。 |
| 查询无结果 | 核对教学班号/课程名、当期批次、登录状态和网络；课程名搜索最多读取接口当前返回的候选。 |
| 开始按钮不可用 | 确认已登录、没有任务正在运行，且待抢列表非空。 |
| 任务立即开始 | “正式时间减提前秒数”已经过去；重新检查日期、时间和提前量。 |
| 显示成功但官方系统未确认 | 脚本是基于返回文本的尽力判断；以学校官方系统记录为准。 |
| 课表缺少课程 | 先在主页面查询课程；若时间字段不能解析，课程不会自动落格。 |

### 安全与合规清单

- 只在自己的电脑上运行，确认地址为本机 `127.0.0.1`。
- 不分享、不上传 `credentials.json`，不用真实凭据做截图或演示。
- 开始前逐项核对教学班号、教师、时间、地点和待抢列表。
- 使用学校允许的请求频率；遇到限流、异常或规则提示立即停止。
- 最终结果以学校官方系统为准，并在使用后关闭服务窗口。

