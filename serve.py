#!/usr/bin/env python3
"""Start the webscan web app, then open it in your browser.

    python3 serve.py                 # http://127.0.0.1:8765
    python3 serve.py --port 9000
"""
from webscan.server import main

if __name__ == "__main__":
    main()
