"""Capture login credentials from Chromium browser traffic using selenium-wire."""

from __future__ import annotations

import atexit
import os
import shutil as shutil_module
import shutil
import tempfile
import time
from pathlib import Path
from typing import Callable, Optional

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BrowserStartupError(Exception):
    """Raised when a supported browser or selenium-wire cannot start."""


def _load_webdriver():
    try:
        from seleniumwire import webdriver
    except ImportError as exc:
        raise BrowserStartupError(
            "selenium-wire is not installed. Run: pip install -r requirements.txt"
        ) from exc
    return webdriver


def _prepare_browser_environment() -> None:
    """Avoid local proxy env and stale chromedriver entries for this process."""
    for key in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
    ):
        os.environ.pop(key, None)

    driver_path = shutil_module.which("chromedriver")
    if not driver_path:
        return

    driver_dir = str(Path(driver_path).resolve().parent)
    path_parts = os.environ.get("PATH", "").split(os.pathsep)
    os.environ["PATH"] = os.pathsep.join(
        part for part in path_parts if str(Path(part).resolve()) != driver_dir
    )


class RequestSniffer:
    """Open Chrome or Edge and wait until a target request is observed."""

    def __init__(self, log: Callable[[str], None] = print):
        self.log = log

    def _make_profile_dir(self) -> str:
        profile_dir = Path(tempfile.gettempdir()) / f"jnu_auto_elective_{os.getpid()}_{int(time.time())}"
        shutil.rmtree(profile_dir, ignore_errors=True)
        profile_dir.mkdir(parents=True, exist_ok=True)
        atexit.register(lambda: shutil.rmtree(profile_dir, ignore_errors=True))
        return str(profile_dir)

    def _build_options(self, webdriver, profile_dir: str, browser_name: str):
        options_cls = webdriver.ChromeOptions if browser_name == "Chrome" else webdriver.EdgeOptions
        options = options_cls()
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--lang=zh-CN")
        if hasattr(options, "add_experimental_option"):
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
        return options

    def _start_browser(self, webdriver, profile_dir: str, seleniumwire_options: dict[str, object]):
        errors: list[str] = []
        for browser_name, factory in (("Chrome", webdriver.Chrome), ("Edge", webdriver.Edge)):
            options = self._build_options(webdriver, profile_dir, browser_name)
            try:
                self.log(f"正在启动 {browser_name}...")
                return browser_name, factory(options=options, seleniumwire_options=seleniumwire_options)
            except Exception as exc:  # noqa: BLE001 - collect browser startup failures for UI log
                errors.append(f"{browser_name}: {exc}")
        detail = "；".join(errors)
        raise BrowserStartupError(f"无法启动 Chrome 或 Edge，请确认已安装浏览器及对应驱动。{detail}")

    def sniff(
        self,
        *,
        visit_url: str,
        target_url: str,
        timeout: int,
        should_stop: Optional[Callable[[], bool]] = None,
    ) -> Optional[dict[str, object]]:
        _prepare_browser_environment()
        webdriver = _load_webdriver()
        profile_dir = self._make_profile_dir()
        seleniumwire_options = {
            "disable_encoding": True,
            "verify_ssl": False,
            "suppress_connection_errors": True,
        }

        browser_name, driver = self._start_browser(webdriver, profile_dir, seleniumwire_options)

        self.log(f"请在 {browser_name} 中完成登录：{visit_url}")
        driver.get(visit_url)
        deadline = time.time() + timeout

        try:
            while time.time() < deadline:
                if should_stop and should_stop():
                    return None
                for request in driver.requests:
                    if request.response and target_url in request.url:
                        headers = {str(key).lower(): value for key, value in dict(request.headers).items()}
                        payload = request.body.decode("utf-8", errors="ignore") if request.body else ""
                        self.log(f"已捕获目标请求：{request.url}")
                        return {
                            "url": request.url,
                            "request_headers": headers,
                            "request_payload": payload,
                        }
                time.sleep(1)
        finally:
            self.log(f"正在关闭 {browser_name}...")
            driver.quit()

        self.log(f"在 {timeout} 秒内未捕获到目标请求。")
        return None
