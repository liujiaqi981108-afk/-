#!/usr/bin/env python3
"""Cross-platform launcher for a dedicated local Chrome window with CDP port 9222 for Google Flow."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_DIR = BASE_DIR / ".chrome_flow_profile"
DEFAULT_FLOW_URL = "https://labs.google/fx/tools/flow"


def find_chrome_binary() -> str:
    """Locate Google Chrome / Chromium / Edge across macOS, Windows, and Linux."""
    env_bin = os.getenv("CHROME_BIN", "").strip()
    if env_bin and Path(env_bin).exists():
        return env_bin

    system = platform.system().lower()
    candidates: list[str] = []

    if system == "darwin":
        candidates.extend(
            [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            ]
        )
    elif system == "windows":
        prog_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        prog_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
        local_app = os.environ.get("LOCALAPPDATA", "")
        for root in (prog_files, prog_x86, local_app):
            if root:
                candidates.append(str(Path(root) / "Google/Chrome/Application/chrome.exe"))
                candidates.append(str(Path(root) / "Microsoft/Edge/Application/msedge.exe"))
    else:
        for name in (
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
            "microsoft-edge",
        ):
            found = shutil.which(name)
            if found:
                candidates.append(found)

    for c in candidates:
        if Path(c).exists():
            return c

    raise FileNotFoundError(
        "未找到本机 Google Chrome / Edge 浏览器可执行文件。请安装 Google Chrome，或设置环境变量 CHROME_BIN=/path/to/chrome。"
    )


def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.8)
        return sock.connect_ex((host, port)) == 0


def launch_chrome(
    port: int = 9222,
    profile_dir: Path = DEFAULT_PROFILE_DIR,
    url: str = DEFAULT_FLOW_URL,
) -> None:
    if is_port_open("127.0.0.1", port):
        print(f"[Flow Chrome] 检测到本地 127.0.0.1:{port} 已处于监听状态，直接复用现有浏览器会话。")
        return

    chrome_bin = find_chrome_binary()
    profile_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        chrome_bin,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        url,
    ]
    print(f"[Flow Chrome] 正在启动本地专属 Chrome 窗口: {chrome_bin}")
    print(f"[Flow Chrome] 登录态持久化目录: {profile_dir}")
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=(platform.system().lower() != "windows"),
    )

    for _ in range(25):
        if is_port_open("127.0.0.1", port):
            print(f"✅ [Flow Chrome] CDP 调试端口 http://127.0.0.1:{port} 已就绪！")
            print("👉 首次使用请在弹出的 Chrome 窗口中手动登录你的 Google 账号并进入 Google Flow 工作台（后续重启自动免登录）。")
            return
        time.sleep(0.4)

    print(
        f"⚠️ [Flow Chrome] 浏览器已启动，但端口 {port} 尚未响应。请检查是否已有占用了同一用户目录的 Chrome 进程。",
        file=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="启动带 CDP 9222 端口的本地 Google Flow 专属 Chrome 窗口")
    parser.add_argument("--port", type=int, default=9222, help="Chrome CDP 远程调试端口 (默认: 9222)")
    parser.add_argument("--profile-dir", type=Path, default=DEFAULT_PROFILE_DIR, help="持久化登录态目录")
    parser.add_argument("--url", default=DEFAULT_FLOW_URL, help="启动打开的 Google Flow 网址")
    args = parser.parse_args()
    launch_chrome(port=args.port, profile_dir=args.profile_dir, url=args.url)


if __name__ == "__main__":
    main()
