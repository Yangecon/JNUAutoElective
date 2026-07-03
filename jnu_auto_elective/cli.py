"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .client import ApiError, CourseClient
from .config import BASE_URL, DEFAULT_BROWSER_TIMEOUT, DEFAULT_INTERVAL, DEFAULT_ROUNDS, XKXF_URL
from .credentials import CredentialError, Credentials
from .sniffer import BrowserStartupError, RequestSniffer
from .web import run_web


def _read_class_ids(path: str | Path) -> list[str]:
    values = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            values.append(line)
    if not values:
        raise ValueError(f"No teaching class ids found in {path}")
    return values


def capture_command(args: argparse.Namespace) -> int:
    sniffer = RequestSniffer()
    try:
        captured = sniffer.sniff(
            visit_url=BASE_URL,
            target_url=XKXF_URL,
            timeout=args.timeout,
        )
    except BrowserStartupError as exc:
        print(f"浏览器启动失败：{exc}", file=sys.stderr)
        return 2

    if not captured:
        print("没有捕获到登录凭据。", file=sys.stderr)
        return 1

    try:
        credentials = Credentials.from_capture(captured)
    except CredentialError as exc:
        print(f"凭据解析失败：{exc}", file=sys.stderr)
        return 1

    credentials.save(args.out)
    print(f"已保存凭据到 {args.out}")
    print(f"学号：{credentials.student_code}，选课批次：{credentials.elective_batch_code}")
    return 0


def run_command(args: argparse.Namespace) -> int:
    try:
        credentials = Credentials.load(args.credentials)
        class_ids = _read_class_ids(args.classes)
    except (CredentialError, OSError, ValueError) as exc:
        print(f"读取配置失败：{exc}", file=sys.stderr)
        return 2

    client = CourseClient(credentials)
    courses = []
    for class_id in class_ids:
        try:
            course = client.search_class(class_id)
        except ApiError as exc:
            print(f"跳过 {class_id}: {exc}")
            continue
        courses.append(course)
        print(f"已找到：{course.summary}")

    if not courses:
        print("没有可提交的课程。", file=sys.stderr)
        return 1

    if args.dry_run:
        print("dry-run 模式结束：未提交选课请求。")
        return 0

    def on_result(course, result):
        print(f"[{course.teaching_class_id}] {course.name}: {result}")

    for round_index in range(args.rounds):
        print(f"开始第 {round_index + 1}/{args.rounds} 轮...")
        client.submit_round(courses, interval=args.interval, on_result=on_result)

    print("提交完成。")
    return 0


def web_command(args: argparse.Namespace) -> int:
    run_web(
        host=args.host,
        port=args.port,
        credentials_path=args.credentials,
        open_browser=not args.no_open,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jnu-auto-elective")
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser("capture", help="capture credentials after browser login")
    capture.add_argument("--out", default="credentials.json", help="credential output path")
    capture.add_argument("--timeout", type=int, default=DEFAULT_BROWSER_TIMEOUT)
    capture.set_defaults(func=capture_command)

    run = subparsers.add_parser("run", help="query classes and submit elective requests")
    run.add_argument("--credentials", default="credentials.json")
    run.add_argument("--classes", default="classes.txt", help="one teaching class id per line")
    run.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    run.add_argument("--interval", type=float, default=DEFAULT_INTERVAL)
    run.add_argument("--dry-run", action="store_true")
    run.set_defaults(func=run_command)

    web = subparsers.add_parser("web", help="start the local monitoring web console")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8765)
    web.add_argument("--credentials", default="credentials.json")
    web.add_argument("--no-open", action="store_true", help="do not open the browser automatically")
    web.set_defaults(func=web_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
