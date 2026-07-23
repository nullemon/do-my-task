#!/usr/bin/env python3
"""Command-line entry point for webscan (no browser).

    python3 scan.py https://mysite.com
    python3 scan.py https://mysite.com --path /app --wordlist sensitive
    python3 scan.py http://203.0.113.10 --host-header mysite.com --spoof-ip 127.0.0.1
"""
import sys
from webscan.cli import main

if __name__ == "__main__":
    sys.exit(main())
