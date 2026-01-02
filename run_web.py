#!/usr/bin/env python3
"""
Launch GradQuest Web UI.

Run with: python run_web.py
Then open http://localhost:5000 in your browser.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from gradquest.web.app import run_server

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='GradQuest Web UI')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', '-p', type=int, default=5000, help='Port to run on')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, debug=args.debug)
