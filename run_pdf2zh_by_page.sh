#!/bin/zsh
set -euo pipefail
cd ~/obsidian/Max-Docs/llm-ccp-propaganda
exec /Library/Developer/CommandLineTools/usr/bin/python3 ./run_pdf2zh_by_page.py "$@"
