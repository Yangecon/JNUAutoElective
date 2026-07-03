"""Local monitoring web UI."""

from __future__ import annotations

import json
import threading
import time
import webbrowser
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .client import ApiError, CourseClient, CourseInfo, is_selection_success
from .config import BASE_URL, DEFAULT_BROWSER_TIMEOUT, DEFAULT_INTERVAL, XKXF_URL
from .credentials import CredentialError, Credentials
from .sniffer import BrowserStartupError, RequestSniffer


try:
    BEIJING_TZ = ZoneInfo("Asia/Shanghai")
except ZoneInfoNotFoundError:
    BEIJING_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")


MAX_CREDENTIAL_AGE_SECONDS = 24 * 60 * 60


INDEX_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JNUAutoElective</title>
  <style>
    :root {
      --bg: oklch(96.5% 0.012 220);
      --panel: oklch(100% 0 0);
      --panel-2: oklch(98.2% 0.006 220);
      --ink: oklch(22% 0.035 230);
      --muted: oklch(45% 0.03 230);
      --line: oklch(88.5% 0.014 230);
      --accent: oklch(43% 0.095 220);
      --accent-2: oklch(43% 0.095 170);
      --ok: oklch(43% 0.12 155);
      --warn: oklch(53% 0.13 65);
      --danger: oklch(45% 0.16 25);
      --shadow: 0 18px 55px rgba(24, 34, 48, .10);
      --shadow-soft: 0 1px 2px rgba(24, 34, 48, .05);
      --focus: rgba(23, 107, 135, .16);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    button, a { font: inherit; }
    .shell {
      min-height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr;
    }
    header {
      height: 64px;
      padding: 0 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    .brand { display: flex; align-items: center; gap: 12px; min-width: 0; }
    .brand-mark {
      width: 34px;
      height: 34px;
      border-radius: 8px;
      display: grid;
      place-items: center;
      color: var(--accent);
      background: oklch(96% 0.025 205);
      box-shadow: inset 0 0 0 1px oklch(88.5% 0.025 205);
      font-weight: 750;
    }
    .brand-copy { min-width: 0; }
    h1 { margin: 0; font-size: 19px; line-height: 1.2; letter-spacing: 0; }
    .brand-copy span { display: block; margin-top: 2px; color: var(--muted); font-size: 12px; }
    .status-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; justify-content: flex-end; }
    .badge {
      min-height: 28px;
      display: inline-flex;
      align-items: center;
      gap: 7px;
      padding: 4px 10px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #fff;
      color: var(--muted);
      white-space: nowrap;
      font-size: 13px;
      box-shadow: var(--shadow-soft);
    }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--muted); }
    .dot.ok { background: var(--ok); }
    .dot.warn { background: var(--warn); }
    .dot.busy { background: var(--accent); }
    main {
      width: min(1180px, calc(100% - 36px));
      margin: 0 auto;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 320px;
      gap: 28px;
      align-items: center;
      padding: 34px 0;
    }
    .launch {
      min-height: min(680px, calc(100vh - 132px));
      display: grid;
      align-content: center;
      gap: 26px;
    }
    .time-label {
      color: var(--muted);
      font-size: 15px;
    }
    .time {
      margin: 0;
      font-size: clamp(64px, 12vw, 150px);
      line-height: .9;
      letter-spacing: 0;
      font-weight: 760;
      font-variant-numeric: tabular-nums;
    }
    .date {
      color: var(--muted);
      font-size: clamp(18px, 2.4vw, 28px);
      font-variant-numeric: tabular-nums;
    }
    .launch-actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
      margin-top: 10px;
    }
    .primary-action,
    .secondary-action {
      min-height: 52px;
      border-radius: 8px;
      border: 1px solid var(--line);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 9px;
      padding: 12px 18px;
      color: var(--ink);
      background: #fff;
      text-decoration: none;
      box-shadow: var(--shadow-soft);
      transition: border-color .16s ease, transform .16s ease, background-color .16s ease;
    }
    .primary-action {
      min-width: 190px;
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
      font-weight: 700;
    }
    .secondary-action { color: var(--muted); }
    .primary-action:hover,
    .secondary-action:hover { border-color: var(--accent); transform: translateY(-1px); }
    .primary-action:focus-visible,
    .secondary-action:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
    aside {
      display: grid;
      gap: 12px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 16px;
    }
    .panel h2 {
      margin: 0 0 10px;
      font-size: 15px;
      letter-spacing: 0;
    }
    .panel p {
      margin: 0;
      color: var(--muted);
      line-height: 1.65;
      font-size: 13px;
    }
    .steps {
      margin: 0;
      padding: 0;
      display: grid;
      gap: 9px;
      list-style: none;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }
    .steps li {
      display: grid;
      grid-template-columns: 24px minmax(0, 1fr);
      gap: 8px;
      align-items: start;
    }
    .steps span {
      width: 24px;
      height: 24px;
      display: grid;
      place-items: center;
      border-radius: 999px;
      background: var(--panel-2);
      color: var(--accent);
      font-weight: 700;
      font-size: 12px;
    }
    .metric {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .metric div {
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-2);
    }
    .metric strong { display: block; font-size: 16px; margin-bottom: 2px; }
    .metric span { color: var(--muted); font-size: 12px; }
    @media (prefers-reduced-motion: reduce) {
      .primary-action, .secondary-action { transition: none; }
      .primary-action:hover, .secondary-action:hover { transform: none; }
    }
    @media (max-width: 860px) {
      header { height: auto; padding: 14px 18px; align-items: flex-start; flex-direction: column; }
      main { grid-template-columns: 1fr; align-items: start; padding-top: 26px; }
      .launch { min-height: auto; }
      .time { font-size: clamp(58px, 18vw, 108px); }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div class="brand">
        <div class="brand-mark">J</div>
        <div class="brand-copy">
          <h1>JNUAutoElective</h1>
          <span>启动页</span>
        </div>
      </div>
      <div class="status-row">
        <span class="badge"><span id="credDot" class="dot"></span><span id="credText">检查凭据中</span></span>
        <span class="badge"><span id="runDot" class="dot"></span><span id="runText">空闲</span></span>
      </div>
    </header>
    <main>
      <section class="launch" aria-label="启动抢课监控台">
        <div class="time-label">北京时间（东八区）</div>
        <p id="clockTime" class="time">--:--:--</p>
        <div id="clockDate" class="date">----</div>
        <div class="launch-actions">
          <a class="primary-action" href="/console">开始</a>
          <a class="secondary-action" href="/schedule">查看课表</a>
        </div>
      </section>
      <aside>
        <section class="panel">
          <h2>抢课前检查</h2>
          <ol class="steps">
            <li><span>1</span><div>提前约 5 分钟进入监控台并完成登录。</div></li>
            <li><span>2</span><div>查询课程，勾选教学班号，加入待抢列表。</div></li>
            <li><span>3</span><div>设置北京时间、提前访问秒数和提交间隔。</div></li>
          </ol>
        </section>
        <section class="panel">
          <h2>默认执行参数</h2>
          <div class="metric">
            <div><strong>60 秒</strong><span>提前访问</span></div>
            <div><strong>0.1 秒</strong><span>提交间隔</span></div>
          </div>
        </section>
        <section class="panel">
          <h2>登录方式</h2>
          <p>网页控制台用系统默认浏览器打开；如果缺少凭据，监控台会自动尝试弹出 Chrome 或 Edge 完成登录捕获。</p>
        </section>
      </aside>
    </main>
  </div>
  <script>
    const credDot = document.querySelector("#credDot");
    const credText = document.querySelector("#credText");
    const runDot = document.querySelector("#runDot");
    const runText = document.querySelector("#runText");
    const clockTime = document.querySelector("#clockTime");
    const clockDate = document.querySelector("#clockDate");

    async function api(path) {
      const response = await fetch(path);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "请求失败");
      return data;
    }

    function updateClock() {
      const now = new Date();
      clockTime.textContent = now.toLocaleTimeString("zh-CN", {
        hour12: false,
        timeZone: "Asia/Shanghai"
      });
      clockDate.textContent = now.toLocaleDateString("zh-CN", {
        weekday: "long",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        timeZone: "Asia/Shanghai"
      });
    }

    function applyState(state) {
      credDot.className = "dot " + (state.credentials.exists ? "ok" : (state.capture.running ? "busy" : "warn"));
      credText.textContent = state.credentials.exists ? `已登录 ${state.credentials.student_code || ""}` : (state.capture.running ? "等待登录" : (state.credentials.expired ? "登录已过期" : "未登录"));
      runDot.className = "dot " + (state.snatch.running ? "busy" : "ok");
      runText.textContent = state.snatch.running ? "抢课中" : "空闲";
    }

    async function refresh() {
      try { applyState(await api("/api/state")); } catch (error) { console.error(error); }
    }

    updateClock();
    refresh();
    setInterval(updateClock, 1000);
    setInterval(refresh, 1500);
  </script>
</body>
</html>
"""


CONSOLE_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JNUAutoElective</title>
  <style>
    :root {
      --bg: oklch(96.5% 0.012 220);
      --panel: oklch(100% 0 0);
      --panel-2: oklch(98.2% 0.006 220);
      --ink: oklch(22% 0.035 230);
      --muted: oklch(45% 0.03 230);
      --line: oklch(88.5% 0.014 230);
      --accent: oklch(43% 0.095 220);
      --accent-2: oklch(43% 0.095 170);
      --soft: oklch(96% 0.025 205);
      --danger: oklch(45% 0.16 25);
      --warn: oklch(53% 0.13 65);
      --ok: oklch(43% 0.12 155);
      --shadow: 0 12px 30px rgba(24, 34, 48, .08);
      --shadow-soft: 0 1px 2px rgba(24, 34, 48, .05);
      --focus: rgba(23, 107, 135, .14);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    button, input, textarea { font: inherit; }
    .app { min-height: 100vh; display: grid; grid-template-rows: auto 1fr; }
    header {
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      padding: 14px 22px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      position: sticky;
      top: 0;
      z-index: 10;
    }
    h1 { margin: 0; font-size: 20px; font-weight: 700; letter-spacing: 0; }
    .brand-copy { display: grid; gap: 2px; }
    .brand-copy span { color: var(--muted); font-size: 12px; }
    .status-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; color: var(--muted); font-size: 13px; }
    .badge {
      min-height: 28px;
      display: inline-flex;
      align-items: center;
      gap: 7px;
      padding: 4px 10px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #fff;
      color: var(--muted);
      white-space: nowrap;
      box-shadow: var(--shadow-soft);
    }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--muted); }
    .dot.ok { background: var(--ok); }
    .dot.warn { background: var(--warn); }
    .dot.busy { background: var(--accent); }
    main {
      display: grid;
      grid-template-columns: minmax(300px, 380px) minmax(0, 1fr);
      gap: 18px;
      padding: 18px;
      max-width: 1320px;
      width: 100%;
      margin: 0 auto;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      min-width: 0;
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand-mark {
      width: 34px;
      height: 34px;
      border-radius: 8px;
      display: grid;
      place-items: center;
      background: var(--soft);
      color: var(--accent);
      font-weight: 750;
      box-shadow: inset 0 0 0 1px oklch(88.5% 0.025 205);
    }
    .top-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .button-link {
      min-height: 34px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 7px 12px;
      text-decoration: none;
      font-size: 13px;
    }
    .button-link.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
    .panel { padding: 18px; }
    .left-rail { display: grid; gap: 16px; align-content: start; }
    .section-title {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 12px;
    }
    .section-title h2,
    .section-title strong {
      margin: 0;
      font-size: 15px;
      font-weight: 700;
      letter-spacing: 0;
    }
    .section-title span { color: var(--muted); font-size: 12px; }
    .section-title.compact { margin: 0; }
    .stack { display: grid; gap: 14px; }
    label { display: grid; gap: 7px; color: var(--muted); font-size: 13px; }
    textarea, input {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      padding: 10px 11px;
      outline: none;
      box-shadow: var(--shadow-soft);
    }
    textarea { min-height: 180px; resize: vertical; line-height: 1.5; font-family: Consolas, "SFMono-Regular", monospace; }
    input:focus, textarea:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--focus); }
    .hint {
      color: var(--muted);
      background: var(--panel-2);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px 11px;
      font-size: 13px;
      line-height: 1.5;
    }
    .run-settings {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 11px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-2);
    }
    .clock-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      grid-column: 1 / -1;
      color: var(--muted);
      font-size: 13px;
    }
    .clock-row strong { color: var(--ink); font-weight: 650; }
    .run-settings .wide { grid-column: 1 / -1; }
    .run-settings .note { grid-column: 1 / -1; color: var(--muted); font-size: 12px; line-height: 1.5; }
    .actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    button {
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 8px 12px;
      box-shadow: var(--shadow-soft);
      transition: background-color .16s ease, border-color .16s ease, color .16s ease, transform .16s ease;
    }
    button:hover:not(:disabled), .button-link:hover { border-color: var(--accent); transform: translateY(-1px); }
    button:focus-visible, .button-link:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
    button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
    button.success { background: var(--accent-2); border-color: var(--accent-2); color: #fff; }
    button.danger { background: #fff; border-color: #f2b8b5; color: var(--danger); }
    button:disabled { opacity: .55; cursor: not-allowed; }
    .right { display: grid; grid-template-rows: auto minmax(300px, 1fr); gap: 16px; min-height: 0; }
    .pending { overflow: hidden; }
    .pending-list { display: grid; gap: 8px; padding: 12px; max-height: 330px; overflow: auto; }
    .pending-item {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 10px;
      align-items: center;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-2);
      font-size: 13px;
      box-shadow: var(--shadow-soft);
    }
    .pending-item strong { display: block; margin-bottom: 3px; }
    .pending-item button { min-height: 32px; padding: 5px 9px; }
    .courses { padding: 0; overflow: hidden; }
    .course-head, .log-head {
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
    }
    .course-list { display: grid; gap: 0; }
    .course {
      display: grid;
      grid-template-columns: 34px minmax(170px, 1.15fr) minmax(115px, .75fr) minmax(95px, .7fr) minmax(130px, .9fr) minmax(180px, 1.1fr);
      gap: 12px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--line);
      align-items: center;
      font-size: 13px;
    }
    .course:hover { background: var(--panel-2); }
    .course:last-child { border-bottom: 0; }
    .course strong { font-size: 14px; }
    .course input[type="checkbox"] { width: 18px; height: 18px; accent-color: var(--accent); }
    .selected-count { color: var(--accent); font-weight: 650; }
    .muted { color: var(--muted); }
    .empty { color: var(--muted); padding: 22px 16px; text-align: center; }
    .log-box { min-height: 0; display: grid; grid-template-rows: auto 1fr; }
    pre {
      margin: 0;
      padding: 14px 16px;
      overflow: auto;
      white-space: pre-wrap;
      line-height: 1.5;
      font-size: 12px;
      font-family: Consolas, "SFMono-Regular", monospace;
      background: #111827;
      color: #edf2fa;
      border-radius: 0 0 8px 8px;
    }
    .overlay {
      position: fixed;
      inset: 0;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 18px;
      background: rgba(16, 24, 40, .48);
      z-index: 20;
    }
    .overlay.show { display: flex; }
    .dialog {
      width: min(520px, 100%);
      background: #fff;
      border-radius: 8px;
      padding: 18px;
      border: 1px solid var(--line);
      box-shadow: 0 24px 80px rgba(0, 0, 0, .22);
    }
    .dialog h2 { margin: 0 0 8px; font-size: 18px; }
    .dialog p { margin: 0 0 14px; color: var(--muted); line-height: 1.6; }
    @media (prefers-reduced-motion: reduce) {
      button, .button-link { transition: none; }
      button:hover:not(:disabled), .button-link:hover { transform: none; }
    }
    @media (max-width: 900px) {
      header { align-items: flex-start; flex-direction: column; }
      main { grid-template-columns: 1fr; }
      .course { grid-template-columns: 1fr; gap: 5px; }
      .run-settings { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="app">
    <header>
      <div class="brand">
        <div class="brand-mark">J</div>
        <div class="brand-copy">
          <h1>JNUAutoElective</h1>
          <span>本地抢课监控台</span>
        </div>
      </div>
      <div class="top-actions">
        <a class="button-link primary" href="/schedule">课表</a>
        <div class="status-row">
          <span class="badge"><span id="credDot" class="dot"></span><span id="credText">检查凭据中</span></span>
          <span class="badge"><span id="runDot" class="dot"></span><span id="runText">空闲</span></span>
        </div>
      </div>
    </header>
    <main>
      <div class="left-rail">
        <section class="panel">
          <div class="stack">
            <div class="section-title">
              <h2>课程查询</h2>
              <span>查询后勾选教学班</span>
            </div>
            <label>每行一个教学班号或课程名称
              <textarea id="classIds" spellcheck="false" placeholder="例如：&#10;高级微观经济学&#10;ABC123-01"></textarea>
            </label>
            <div class="hint">课程名可能返回多个教学班。候选结果只用于选择；真正执行抢课的是待抢列表。</div>
            <div class="run-settings">
              <div class="clock-row"><span>北京时间（东八区）</span><strong id="localClock">--:--:--</strong></div>
              <label class="wide">正式开抢时间（北京时间）
                <input id="startAt" type="datetime-local" value="2026-06-25T13:00">
              </label>
              <label>提前访问秒数
                <input id="leadSeconds" type="number" min="0" step="1" value="60">
              </label>
              <label>提交间隔秒
                <input id="interval" type="number" min="0.02" step="0.01" value="0.1">
              </label>
              <div class="note">后端按 Asia/Shanghai 解释时间；如果提前量计算后的时间已过，会立即进入高频提交。</div>
            </div>
            <div class="actions">
              <button id="queryBtn" type="button">查询课程</button>
              <button id="addPendingBtn" type="button">加入待抢</button>
              <button id="loginBtn" class="primary" type="button">重新登录</button>
              <button id="startBtn" class="success" type="button">开始抢课</button>
            </div>
          </div>
        </section>
        <section class="pending">
          <div class="course-head"><div class="section-title compact"><strong>待抢列表</strong><span>开始后只提交这里</span></div><span id="pendingCount" class="muted">0 个</span></div>
          <div id="pendingList" class="pending-list"><div class="empty">从候选课程勾选教学班后加入这里。</div></div>
          <div class="actions" style="padding: 0 12px 12px;">
            <button id="clearPendingBtn" type="button">清空待抢</button>
            <button id="stopBtn" class="danger" type="button">停止抢课</button>
          </div>
        </section>
      </div>
      <div class="right">
        <section class="courses">
          <div class="course-head"><div class="section-title compact"><strong>课程候选</strong><span>可多选加入待抢</span></div><span id="courseCount" class="muted">0 门</span></div>
          <div id="courseList" class="course-list"><div class="empty">还没有课程，先输入教学班号或课程名称并查询。</div></div>
        </section>
        <section class="log-box">
          <div class="log-head"><div class="section-title compact"><strong>运行日志</strong><span>登录、查询、提交结果</span></div><button id="clearLogBtn" type="button">清空显示</button></div>
          <pre id="log"></pre>
        </section>
      </div>
    </main>
  </div>
  <div id="loginOverlay" class="overlay">
    <div class="dialog">
      <h2>需要登录</h2>
      <p>本地没有可用凭据，程序正在尝试打开 Chrome 或 Edge。请在弹出的浏览器中完成暨南大学选课系统登录；捕获成功后窗口会自动关闭，监控页面会继续。</p>
      <button id="retryLoginBtn" class="primary" type="button">再次打开登录</button>
    </div>
  </div>
  <script>
    const logEl = document.querySelector("#log");
    const credDot = document.querySelector("#credDot");
    const credText = document.querySelector("#credText");
    const runDot = document.querySelector("#runDot");
    const runText = document.querySelector("#runText");
    const courseList = document.querySelector("#courseList");
    const courseCount = document.querySelector("#courseCount");
    const pendingList = document.querySelector("#pendingList");
    const pendingCount = document.querySelector("#pendingCount");
    const localClock = document.querySelector("#localClock");
    const overlay = document.querySelector("#loginOverlay");
    let loginAutoStarted = false;
    let selectedClassIds = new Set();

    function appendLog(line) {
      const atBottom = logEl.scrollTop + logEl.clientHeight >= logEl.scrollHeight - 20;
      logEl.textContent += line + "\n";
      if (atBottom) logEl.scrollTop = logEl.scrollHeight;
    }

    async function api(path, options = {}) {
      const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "请求失败");
      return data;
    }

    function classIds() {
      return document.querySelector("#classIds").value.split(/\r?\n/).map(x => x.trim()).filter(Boolean);
    }

    function wantedClassIds() {
      return Array.from(selectedClassIds);
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[ch]));
    }

    function updateLocalClock() {
      const now = new Date();
      localClock.textContent = now.toLocaleString("zh-CN", {
        hour12: false,
        timeZone: "Asia/Shanghai"
      });
    }

    function renderCourses(courses) {
      courseCount.innerHTML = `${courses.length} 门候选 · <span class="selected-count">${selectedClassIds.size}</span> 个已选`;
      if (!courses.length) {
        courseList.innerHTML = '<div class="empty">还没有课程，先输入教学班号或课程名称并查询。</div>';
        return;
      }
      courseList.innerHTML = courses.map(course => `
        <div class="course">
          <input class="course-select" type="checkbox" value="${escapeHtml(course.teaching_class_id || "")}" ${selectedClassIds.has(course.teaching_class_id) ? "checked" : ""} aria-label="选择 ${escapeHtml(course.teaching_class_id || "")}">
          <div><strong>${escapeHtml(course.name || "未命名课程")}</strong><div class="muted">${escapeHtml(course.course_number || "")}</div></div>
          <div><span class="muted">班号</span><br>${escapeHtml(course.teaching_class_id || "")}</div>
          <div><span class="muted">教师</span><br>${escapeHtml(course.teacher || "")}</div>
          <div><span class="muted">开课单位</span><br>${escapeHtml(course.department || "")}</div>
          <div class="muted">${escapeHtml(course.schedule_text || course.time_text || "")}<br>${escapeHtml(course.campus_name || "")} ${escapeHtml(course.place || "")}</div>
        </div>
      `).join("");
      courseList.querySelectorAll(".course-select").forEach(input => {
        input.addEventListener("change", () => {
          if (input.checked) selectedClassIds.add(input.value);
          else selectedClassIds.delete(input.value);
          renderCourses(courses);
        });
      });
    }

    function renderPending(courses) {
      pendingCount.textContent = `${courses.length} 个`;
      if (!courses.length) {
        pendingList.innerHTML = '<div class="empty">从候选课程勾选教学班后加入这里。</div>';
        return;
      }
      pendingList.innerHTML = courses.map(course => `
        <div class="pending-item">
          <div>
            <strong>${escapeHtml(course.name || "未命名课程")}</strong>
            <div class="muted">${escapeHtml(course.teaching_class_id || "")} · ${escapeHtml(course.teacher || "")}</div>
          </div>
          <button class="remove-pending" type="button" data-class-id="${escapeHtml(course.teaching_class_id || "")}">移除</button>
        </div>
      `).join("");
      pendingList.querySelectorAll(".remove-pending").forEach(button => {
        button.addEventListener("click", async () => {
          try {
            await api("/api/pending/remove", {
              method: "POST",
              body: JSON.stringify({ class_id: button.dataset.classId })
            });
            await refresh();
          } catch (error) { appendLog(`[待抢] ${error.message}`); }
        });
      });
    }

    function applyState(state) {
      credDot.className = "dot " + (state.credentials.exists ? "ok" : (state.capture.running ? "busy" : "warn"));
      credText.textContent = state.credentials.exists ? `已登录 ${state.credentials.student_code || ""}` : (state.capture.running ? "等待登录" : (state.credentials.expired ? "登录已过期" : "未登录"));
      runDot.className = "dot " + (state.snatch.running ? "busy" : "ok");
      runText.textContent = state.snatch.running ? "抢课中" : "空闲";
      overlay.classList.toggle("show", !state.credentials.exists);
      renderCourses(state.courses || []);
      renderPending(state.pending_courses || []);
      document.querySelector("#startBtn").disabled = !state.credentials.exists || state.snatch.running;
      document.querySelector("#queryBtn").disabled = !state.credentials.exists || state.snatch.running;
      document.querySelector("#addPendingBtn").disabled = !state.credentials.exists || state.snatch.running;
      document.querySelector("#clearPendingBtn").disabled = state.snatch.running;
      document.querySelector("#stopBtn").disabled = !state.snatch.running;
      if (!state.credentials.exists && !state.capture.running && !loginAutoStarted) {
        loginAutoStarted = true;
        startCapture();
      }
    }

    async function refresh() {
      try { applyState(await api("/api/state")); } catch (error) { appendLog(`[页面] ${error.message}`); }
    }

    async function startCapture() {
      try {
        await api("/api/capture/start", { method: "POST", body: "{}" });
        appendLog("[页面] 已请求打开登录浏览器。");
      } catch (error) { appendLog(`[登录] ${error.message}`); }
    }

    document.querySelector("#loginBtn").addEventListener("click", startCapture);
    document.querySelector("#retryLoginBtn").addEventListener("click", startCapture);
    document.querySelector("#clearLogBtn").addEventListener("click", () => { logEl.textContent = ""; });
    document.querySelector("#queryBtn").addEventListener("click", async () => {
      try {
        await api("/api/classes/query", { method: "POST", body: JSON.stringify({ class_ids: classIds() }) });
        selectedClassIds = new Set();
        await refresh();
      } catch (error) { appendLog(`[查询] ${error.message}`); }
    });
    document.querySelector("#addPendingBtn").addEventListener("click", async () => {
      try {
        const selected = wantedClassIds();
        if (!selected.length) {
          appendLog("[待抢] 请先在候选课程里勾选教学班号。");
          return;
        }
        await api("/api/pending/add", {
          method: "POST",
          body: JSON.stringify({ class_ids: selected })
        });
        selectedClassIds = new Set();
        await refresh();
      } catch (error) { appendLog(`[待抢] ${error.message}`); }
    });
    document.querySelector("#startBtn").addEventListener("click", async () => {
      try {
        await api("/api/snatch/start", {
          method: "POST",
          body: JSON.stringify({
            interval: Number(document.querySelector("#interval").value || 0.1),
            start_at: document.querySelector("#startAt").value,
            lead_seconds: Number(document.querySelector("#leadSeconds").value || 60)
          })
        });
        await refresh();
      } catch (error) { appendLog(`[抢课] ${error.message}`); }
    });
    document.querySelector("#clearPendingBtn").addEventListener("click", async () => {
      try {
        await api("/api/pending/clear", { method: "POST", body: "{}" });
        await refresh();
      } catch (error) { appendLog(`[待抢] ${error.message}`); }
    });
    document.querySelector("#stopBtn").addEventListener("click", async () => {
      try {
        await api("/api/snatch/stop", { method: "POST", body: "{}" });
        appendLog("[页面] 已请求停止。");
      } catch (error) { appendLog(`[停止] ${error.message}`); }
    });
    async function pollLogs() {
      try {
        const data = await api("/api/logs");
        data.logs.forEach(appendLog);
      } catch (error) { appendLog(`[日志] ${error.message}`); }
    }
    refresh();
    pollLogs();
    updateLocalClock();
    setInterval(refresh, 1000);
    setInterval(pollLogs, 700);
    setInterval(updateLocalClock, 1000);
  </script>
</body>
</html>
"""


SCHEDULE_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JNUAutoElective - 课表</title>
  <style>
    :root {
      --bg: oklch(96.5% 0.012 220);
      --panel: oklch(100% 0 0);
      --panel-2: oklch(98.2% 0.006 220);
      --ink: oklch(22% 0.035 230);
      --muted: oklch(45% 0.03 230);
      --line: oklch(88.5% 0.014 230);
      --accent: oklch(43% 0.095 220);
      --ok: oklch(43% 0.12 155);
      --shadow: 0 12px 30px rgba(24, 34, 48, .08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    header {
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      padding: 14px 22px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
    }
    .left { display: flex; align-items: center; gap: 12px; }
    a.back {
      min-height: 34px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 7px 12px;
      border: 1px solid var(--line);
      border-radius: 6px;
      color: var(--ink);
      background: #fff;
      text-decoration: none;
      font-size: 13px;
    }
    h1 { margin: 0; font-size: 20px; font-weight: 650; letter-spacing: 0; }
    .muted { color: var(--muted); }
    main {
      padding: 18px;
      max-width: 1480px;
      margin: 0 auto;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .head {
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .schedule-grid {
      overflow: auto;
      display: grid;
      grid-template-columns: 48px repeat(7, minmax(130px, 1fr));
      grid-auto-rows: minmax(64px, auto);
      font-size: 12px;
      max-height: calc(100vh - 150px);
    }
    .schedule-cell {
      border-right: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
      padding: 7px;
      min-width: 0;
      background: #fff;
    }
    .schedule-head {
      position: sticky;
      top: 0;
      z-index: 3;
      background: var(--panel-2);
      font-weight: 650;
      text-align: center;
    }
    .section-head {
      position: sticky;
      left: 0;
      z-index: 2;
      background: var(--panel-2);
      color: var(--muted);
      text-align: center;
      font-weight: 650;
    }
    .corner { left: 0; z-index: 4; }
    .schedule-course {
      border-left: 3px solid var(--accent);
      background: oklch(96% 0.025 205);
      padding: 7px;
      border-radius: 6px;
      line-height: 1.4;
      margin-bottom: 5px;
    }
    .schedule-course strong {
      display: block;
      font-size: 12px;
      color: var(--ink);
      margin-bottom: 2px;
    }
    .note {
      padding: 10px 16px;
      color: var(--muted);
      font-size: 12px;
      border-top: 1px solid var(--line);
      background: var(--panel-2);
    }
    .empty {
      padding: 28px;
      text-align: center;
      color: var(--muted);
    }
    @media (max-width: 900px) {
      header { align-items: flex-start; flex-direction: column; }
      .schedule-grid { grid-template-columns: 42px repeat(7, minmax(105px, 1fr)); }
    }
  </style>
</head>
<body>
  <header>
    <div class="left">
      <a class="back" href="/console">返回监控台</a>
      <h1>一周课表</h1>
    </div>
    <div id="summary" class="muted">加载中</div>
  </header>
  <main>
    <section>
      <div class="head"><strong>周一到周日</strong><span class="muted">每天 1-13 节</span></div>
      <div id="scheduleGrid" class="schedule-grid"></div>
      <div class="note">课表来自当前页面已查询到的课程；如果教务返回的时间字段能解析出星期和节次，课程会自动落入对应格子。</div>
    </section>
  </main>
  <script>
    const scheduleGrid = document.querySelector("#scheduleGrid");
    const summary = document.querySelector("#summary");

    async function api(path) {
      const response = await fetch(path);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "请求失败");
      return data;
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[ch]));
    }

    function renderSchedule(courses) {
      summary.textContent = `${courses.length} 门课程`;
      const days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
      const cells = new Map();
      courses.forEach(course => {
        (course.schedule_items || []).forEach(item => {
          const start = Number(item.start);
          const end = Number(item.end || item.start);
          const weekday = Number(item.weekday);
          if (!weekday || weekday < 1 || weekday > 7 || !start) return;
          for (let section = start; section <= Math.min(end, 13); section += 1) {
            const key = `${weekday}-${section}`;
            if (!cells.has(key)) cells.set(key, []);
            cells.get(key).push({ course, item, first: section === start });
          }
        });
      });

      let html = '<div class="schedule-cell schedule-head corner"></div>';
      days.forEach(day => { html += `<div class="schedule-cell schedule-head">${day}</div>`; });
      for (let section = 1; section <= 13; section += 1) {
        html += `<div class="schedule-cell section-head">${section}</div>`;
        for (let weekday = 1; weekday <= 7; weekday += 1) {
          const entries = cells.get(`${weekday}-${section}`) || [];
          html += '<div class="schedule-cell">';
          html += entries.map(entry => `
            <div class="schedule-course">
              <strong>${escapeHtml(entry.first ? entry.course.name : "同上")}</strong>
              <span>${escapeHtml(entry.course.teacher || "")}</span><br>
              <span>${escapeHtml(entry.course.place || entry.item.place || "")}</span>
            </div>
          `).join("");
          html += '</div>';
        }
      }
      scheduleGrid.innerHTML = html;
      if (!courses.length) {
        scheduleGrid.insertAdjacentHTML("afterend", '<div class="empty">还没有课程。先返回主页面查询课程。</div>');
      }
    }

    async function refresh() {
      try {
        const state = await api("/api/state");
        renderSchedule(state.courses || []);
      } catch (error) {
        scheduleGrid.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
      }
    }

    refresh();
    setInterval(refresh, 1500);
  </script>
</body>
</html>
"""


class WebState:
    def __init__(self, credentials_path: Path):
        self.credentials_path = credentials_path
        self.lock = threading.Lock()
        self.logs: list[str] = []
        self.log_cursor = 0
        self.courses: list[CourseInfo] = []
        self.pending_courses: list[CourseInfo] = []
        self.capture_running = False
        self.snatch_running = False
        self.stop_event = threading.Event()

    def log(self, message: str) -> None:
        line = f"{time.strftime('%H:%M:%S')} {message}"
        with self.lock:
            self.logs.append(line)
            self.logs = self.logs[-500:]

    def consume_logs(self) -> list[str]:
        with self.lock:
            logs = self.logs[self.log_cursor :]
            self.log_cursor = len(self.logs)
            return logs

    def credentials_info(self) -> dict[str, Any]:
        if not self.credentials_path.exists():
            return {"exists": False, "expired": False, "student_code": None, "elective_batch_code": None}
        age_seconds = time.time() - self.credentials_path.stat().st_mtime
        if age_seconds > MAX_CREDENTIAL_AGE_SECONDS:
            return {
                "exists": False,
                "expired": True,
                "age_seconds": age_seconds,
                "student_code": None,
                "elective_batch_code": None,
            }
        try:
            credentials = Credentials.load(self.credentials_path)
        except (OSError, CredentialError, json.JSONDecodeError):
            return {"exists": False, "expired": False, "student_code": None, "elective_batch_code": None}
        return {
            "exists": True,
            "expired": False,
            "age_seconds": age_seconds,
            "student_code": credentials.student_code,
            "elective_batch_code": credentials.elective_batch_code,
        }

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            courses = [asdict(course) for course in self.courses]
            pending_courses = [asdict(course) for course in self.pending_courses]
            capture_running = self.capture_running
            snatch_running = self.snatch_running
        return {
            "credentials": self.credentials_info(),
            "capture": {"running": capture_running},
            "snatch": {"running": snatch_running},
            "courses": courses,
            "pending_courses": pending_courses,
        }


def _json_response(handler: BaseHTTPRequestHandler, status: HTTPStatus, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status.value)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or "0")
    if length <= 0:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


def _load_credentials(state: WebState) -> Credentials:
    if not state.credentials_path.exists():
        raise CredentialError("请先登录捕获凭据。")
    age_seconds = time.time() - state.credentials_path.stat().st_mtime
    if age_seconds > MAX_CREDENTIAL_AGE_SECONDS:
        raise CredentialError("本地 credentials 已超过 1 天，请重新登录捕获凭据。")
    return Credentials.load(state.credentials_path)


def _query_courses(state: WebState, queries: list[str]) -> list[CourseInfo]:
    if not queries:
        raise ValueError("请至少输入一个教学班号或课程名称。")
    client = CourseClient(_load_credentials(state))
    courses: list[CourseInfo] = []
    for query in queries:
        try:
            found_courses = client.search_courses(query)
        except ApiError as exc:
            state.log(f"[查询] 跳过 {query}: {exc}")
            continue
        courses.extend(found_courses)
        state.log(f"[查询] {query} 找到 {len(found_courses)} 个候选。")
        for course in found_courses:
            state.log(f"[查询] 候选 {course.summary}")
    if not courses:
        raise ValueError("没有查询到可用课程。")
    with state.lock:
        state.courses = courses
    return courses


def _add_pending_courses(state: WebState, class_ids: list[str]) -> list[CourseInfo]:
    if not class_ids:
        raise ValueError("请先勾选要加入待抢列表的教学班号。")
    wanted = set(class_ids)
    with state.lock:
        known = {course.teaching_class_id: course for course in state.courses}
        pending = {course.teaching_class_id: course for course in state.pending_courses}
        for class_id in wanted:
            course = known.get(class_id)
            if course is not None:
                pending[class_id] = course
        state.pending_courses = list(pending.values())
        pending_courses = list(state.pending_courses)
    added = [course for course in pending_courses if course.teaching_class_id in wanted]
    if not added:
        raise ValueError("没有找到可加入待抢列表的候选课程，请先查询课程。")
    state.log(f"[待抢] 已加入 {len(added)} 个教学班。")
    return pending_courses


def _remove_pending_course(state: WebState, class_id: str) -> list[CourseInfo]:
    with state.lock:
        state.pending_courses = [
            course for course in state.pending_courses if course.teaching_class_id != class_id
        ]
        pending_courses = list(state.pending_courses)
    state.log(f"[待抢] 已移除 {class_id}。")
    return pending_courses


def _clear_pending_courses(state: WebState) -> None:
    with state.lock:
        state.pending_courses = []
    state.log("[待抢] 已清空待抢列表。")


def _parse_beijing_start_at(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        start_at = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("开始时间格式不正确，请使用页面里的日期时间控件。") from exc
    if start_at.tzinfo is None:
        start_at = start_at.replace(tzinfo=BEIJING_TZ)
    else:
        start_at = start_at.astimezone(BEIJING_TZ)
    return start_at


def _start_capture(state: WebState) -> None:
    with state.lock:
        if state.capture_running:
            return
        state.capture_running = True

    def worker() -> None:
        try:
            state.log("[登录] 正在打开 Chrome 或 Edge，请完成登录。")
            captured = RequestSniffer(log=lambda msg: state.log(f"[登录] {msg}")).sniff(
                visit_url=BASE_URL,
                target_url=XKXF_URL,
                timeout=DEFAULT_BROWSER_TIMEOUT,
            )
            if not captured:
                state.log("[登录] 未捕获到凭据。")
                return
            credentials = Credentials.from_capture(captured)
            credentials.save(state.credentials_path)
            state.log(f"[登录] 凭据已保存，学号 {credentials.student_code}。")
        except (BrowserStartupError, CredentialError, OSError) as exc:
            state.log(f"[登录] 失败: {exc}")
        finally:
            with state.lock:
                state.capture_running = False

    threading.Thread(target=worker, daemon=True).start()


def _start_snatch(
    state: WebState,
    interval: float,
    start_at: datetime | None,
    lead_seconds: float,
) -> None:
    with state.lock:
        if state.snatch_running:
            raise RuntimeError("抢课任务已经在运行。")
        courses = list(state.pending_courses)
        if not courses:
            raise ValueError("待抢列表为空，请先把候选课程加入待抢列表。")
        state.snatch_running = True
        state.stop_event.clear()

    def worker() -> None:
        try:
            client = CourseClient(_load_credentials(state))
            if start_at is not None:
                effective_start_at = start_at - timedelta(seconds=max(0.0, lead_seconds))
                now = datetime.now(BEIJING_TZ)
                if effective_start_at > now:
                    state.log(
                        "[抢课] 已预约北京时间 "
                        f"{start_at.strftime('%Y-%m-%d %H:%M:%S')} 正式开抢，"
                        f"提前 {lead_seconds:g} 秒开始访问。"
                    )
                    while not state.stop_event.is_set():
                        remaining = (effective_start_at - datetime.now(BEIJING_TZ)).total_seconds()
                        if remaining <= 0:
                            break
                        time.sleep(min(0.2, remaining))
                else:
                    state.log("[抢课] 按提前量计算的开始时间已过，立即进入抢课循环。")
            if state.stop_event.is_set():
                state.log("[抢课] 已在开始前停止。")
                return
            attempt = 0
            while not state.stop_event.is_set():
                attempt += 1
                state.log(f"[抢课] 开始第 {attempt} 轮，选上后自动停止。")
                for index, course in enumerate(courses):
                    if state.stop_event.is_set():
                        break
                    try:
                        result = client.submit(course)
                    except ApiError as exc:
                        result = str(exc)
                    state.log(f"[抢课] {course.teaching_class_id} {course.name}: {result}")
                    if is_selection_success(result):
                        state.log(f"[抢课] 已判断选上：{course.teaching_class_id} {course.name}。")
                        state.stop_event.set()
                        break
                    if index < len(courses) - 1:
                        time.sleep(interval)
                if not state.stop_event.is_set():
                    time.sleep(interval)
            state.log("[抢课] 任务结束。")
        except (CredentialError, ValueError, RuntimeError, OSError) as exc:
            state.log(f"[抢课] 失败: {exc}")
        finally:
            with state.lock:
                state.snatch_running = False

    threading.Thread(target=worker, daemon=True).start()


def make_handler(state: WebState):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/":
                body = INDEX_HTML.encode("utf-8")
                self.send_response(HTTPStatus.OK.value)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path == "/console":
                body = CONSOLE_HTML.encode("utf-8")
                self.send_response(HTTPStatus.OK.value)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path == "/schedule":
                body = SCHEDULE_HTML.encode("utf-8")
                self.send_response(HTTPStatus.OK.value)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path == "/api/state":
                _json_response(self, HTTPStatus.OK, state.snapshot())
                return
            if path == "/api/logs":
                _json_response(self, HTTPStatus.OK, {"logs": state.consume_logs()})
                return
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "Not found"})

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            try:
                payload = _read_json(self)
                if path == "/api/capture/start":
                    _start_capture(state)
                    _json_response(self, HTTPStatus.OK, {"ok": True})
                    return
                if path == "/api/classes/query":
                    class_ids = [str(item).strip() for item in payload.get("class_ids", []) if str(item).strip()]
                    courses = _query_courses(state, class_ids)
                    _json_response(self, HTTPStatus.OK, {"courses": [asdict(course) for course in courses]})
                    return
                if path == "/api/pending/add":
                    class_ids = [str(item).strip() for item in payload.get("class_ids", []) if str(item).strip()]
                    courses = _add_pending_courses(state, class_ids)
                    _json_response(self, HTTPStatus.OK, {"pending_courses": [asdict(course) for course in courses]})
                    return
                if path == "/api/pending/remove":
                    class_id = str(payload.get("class_id", "")).strip()
                    courses = _remove_pending_course(state, class_id)
                    _json_response(self, HTTPStatus.OK, {"pending_courses": [asdict(course) for course in courses]})
                    return
                if path == "/api/pending/clear":
                    _clear_pending_courses(state)
                    _json_response(self, HTTPStatus.OK, {"ok": True})
                    return
                if path == "/api/snatch/start":
                    interval = max(0.02, float(payload.get("interval") or DEFAULT_INTERVAL))
                    start_at = _parse_beijing_start_at(str(payload.get("start_at", "")))
                    lead_seconds = max(0.0, float(payload.get("lead_seconds") or 60))
                    _start_snatch(state, interval, start_at, lead_seconds)
                    _json_response(self, HTTPStatus.OK, {"ok": True})
                    return
                if path == "/api/snatch/stop":
                    state.stop_event.set()
                    _json_response(self, HTTPStatus.OK, {"ok": True})
                    return
                _json_response(self, HTTPStatus.NOT_FOUND, {"error": "Not found"})
            except Exception as exc:  # noqa: BLE001 - report API errors to local UI
                _json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    return Handler


def run_web(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    credentials_path: str | Path = "credentials.json",
    open_browser: bool = True,
) -> None:
    state = WebState(Path(credentials_path))
    server = ThreadingHTTPServer((host, port), make_handler(state))
    url = f"http://{host}:{port}/"
    state.log(f"[系统] 控制台已启动: {url}")
    if state.credentials_info().get("expired"):
        state.log("[登录] 本地 credentials 已超过 1 天，将自动重新登录并覆盖旧文件。")
        _start_capture(state)
    if open_browser:
        webbrowser.open(url)
    try:
        print(f"JNUAutoElective web console: {url}")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping web console.")
    finally:
        server.server_close()
