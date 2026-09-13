#!/usr/bin/env python3
"""
Authentication & Signature Token Utilities for Chhattisgarh Cyber Jagriti Portal.
Vendor endpoint signature implementation: 5-layer base64-encoded unix timestamp.
"""

import base64
import time

def get_url_token():
    """
    Generates the 5-layer base64-encoded unix timestamp query parameter token required by
    https://cyberjagriti.policemitanrpr.com anti-scraping endpoint guard.
    Equivalent to frontend: btoa(btoa(btoa(btoa(btoa(str(Math.floor(Date.now()/1000)))))))
    """
    t = str(int(time.time()))
    for _ in range(5):
        t = base64.b64encode(t.encode('utf-8')).decode('utf-8')
    return t
