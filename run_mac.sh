#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ 未检测到 python3，请先运行: xcode-select --install 或从 https://www.python.org 下载安装 Python 3。"
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "📦 正在创建本地虚拟环境 .venv ..."
  python3 -m venv .venv
fi

source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "🚀 正在启动本地专属 Chrome (端口 9222) 与 9-Agent 影视制片厂..."
exec python3 scripts/start_flow_studio.py "$@"
