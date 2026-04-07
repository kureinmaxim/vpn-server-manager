#!/bin/bash
# Простой launcher для VPN Server Manager

cd "$(dirname "$0")"
source venv/bin/activate
python3 run_desktop.py

