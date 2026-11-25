#!/usr/bin/env python3
"""One-command local launcher: starts Chrome CDP (Google Flow) + 9-Agent Studio Server."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import uvicorn  # noqa: E402
from scripts.launch_local_chrome import launch_chrome  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="一键启动本地 Google Flow + 9-Agent 影视制片厂")
    parser.add_argument("--host", default="127.0.0.1", help="Web 服务监听地址 (默认: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Web 服务端口 (默认: 8000)")
    parser.add_argument("--cdp-port", type=int, default=9222, help="本地 Chrome CDP 端口 (默认: 9222)")
    parser.add_argument(
        "--mock-only",
        action="store_true",
        help="不启动本地 Chrome，仅以纯离线 Mock 引擎运行工作台",
    )
    args = parser.parse_args()

    if not args.mock_only:
        try:
            launch_chrome(port=args.cdp_port)
            os.environ.setdefault("FLOW_CDP_URL", f"http://127.0.0.1:{args.cdp_port}")
            os.environ.setdefault("STUDIO_IMAGE_VENDOR", "flow_browser")
            os.environ.setdefault("STUDIO_VIDEO_VENDOR", "flow_browser")
            os.environ.setdefault("STUDIO_TTS_VENDOR", "edge_tts")
        except FileNotFoundError as exc:
            print(f"⚠️ {exc}\n将先以离线模式启动 Web 工作台，你仍可手动上传 Google Flow 生成的 .mp4 片段。")

    print("\n" + "=" * 72)
    print(f"🎬 9-Agent 短视频制片厂已启动！请在本机浏览器打开: http://{args.host}:{args.port}")
    print("=" * 72 + "\n")
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
