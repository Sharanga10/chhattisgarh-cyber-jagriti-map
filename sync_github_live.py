#!/usr/bin/env python3
"""
Cyber Jagriti Abhiyan - GitHub Actions Live Sync Engine
Lightweight, zero-database sync engine that fetches real-time telemetry from
the Chhattisgarh Police Cyber Jagriti Portal API and keeps live_feed.json updated.
"""

import os
import sys
import time
import json
import requests
from datetime import datetime
from token_utils import get_url_token

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEED_JSON = os.path.join(BASE_DIR, 'live_feed.json')
INDEX_HTML = os.path.join(BASE_DIR, 'index.html')
MAP_HTML = os.path.join(BASE_DIR, 'chhattisgarh_cyber_jagriti_map.html')

CHROME_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Origin": "https://cyberjagriti.policemitanrpr.com",
    "Referer": "https://cyberjagriti.policemitanrpr.com/dashboard",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin"
}

def sync_live():
    print(f"[*] [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting GitHub Live Sync check...")
    
    session = requests.Session()
    session.headers.update(CHROME_HEADERS)

    # 1. Login to Portal
    login_url = "https://cyberjagriti.policemitanrpr.com/api/login/check"
    try:
        r_auth = session.post(login_url, json={"username": "admin", "***REMOVED***": "***REMOVED***"}, timeout=15)
        r_auth.raise_for_status()
        token = r_auth.json().get("token")
        if not token:
            print("[!] Auth failed: Token missing from response.")
            sys.exit(1)
    except Exception as e:
        print(f"[!] Authentication error: {e}")
        sys.exit(1)

    # 2. Fetch Live Dashboard Metrics
    dash_url = f"https://cyberjagriti.policemitanrpr.com/api/cyber_crime/dashboard?token={get_url_token()}"
    try:
        r_dash = session.get(dash_url, headers={"Authorization": token}, timeout=15)
        r_dash.raise_for_status()
        dash_data = r_dash.json()
    except Exception as e:
        print(f"[!] Dashboard fetch error: {e}")
        sys.exit(1)

    counter = dash_data.get("counter", {})
    remote_total_events = int(counter.get("total_entries", 0))
    remote_total_reach = int(counter.get("total_members", 0))
    remote_districts = dash_data.get("districts", [])

    if remote_total_events == 0:
        print("[!] Warning: Remote total entries is 0. Aborting update.")
        sys.exit(0)

    # 3. Load Existing Feed
    if not os.path.exists(FEED_JSON):
        print("[!] live_feed.json not found.")
        sys.exit(1)

    with open(FEED_JSON, 'r', encoding='utf-8') as f:
        current_feed = json.load(f)

    current_events = current_feed.get("total_events", 0)
    current_reach = current_feed.get("total_reach", 0)

    print(f"[*] Current Feed: {current_events:,} events | Remote Portal: {remote_total_events:,} events")

    # Build district alias lookup
    districts_list = current_feed.get("districts", [])
    district_map = {d["name_en"].lower(): d for d in districts_list}
    district_map_hi = {d["name_hi"]: d for d in districts_list}

    # Match remote districts
    for rd in remote_districts:
        r_name_en = rd.get("district_name_en", "").strip().lower()
        r_name_hi = rd.get("district_name_hi", "").strip()
        r_events = int(rd.get("total", 0))
        r_reach = int(rd.get("total_members", 0))

        target = district_map.get(r_name_en) or district_map_hi.get(r_name_hi)
        if not target:
            # Fuzzy match aliases
            for d in districts_list:
                for a in d.get("aliases", []):
                    if a.lower() == r_name_en or a == r_name_hi:
                        target = d
                        break
                if target:
                    break

        if target:
            target["events"] = r_events
            target["reach"] = r_reach
            target["avg_attendance"] = round(r_reach / r_events, 1) if r_events > 0 else 0.0

    # Sort districts by events descending and assign ranks
    districts_list.sort(key=lambda d: d["events"], reverse=True)
    for idx, d in enumerate(districts_list):
        d["rank"] = idx + 1

    # Recalculate State Averages
    calc_total_events = sum(d["events"] for d in districts_list)
    calc_total_reach = sum(d["reach"] for d in districts_list)
    calc_avg_attendance = round(calc_total_reach / calc_total_events, 1) if calc_total_events > 0 else 0.0

    # Ensure we use the official remote total if higher
    final_total_events = max(calc_total_events, remote_total_events)
    final_total_reach = max(calc_total_reach, remote_total_reach)

    has_changes = (final_total_events != current_events) or (final_total_reach != current_reach)

    updated_feed = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_events": final_total_events,
        "total_reach": final_total_reach,
        "avg_attendance": calc_avg_attendance,
        "districts_count": len(districts_list),
        "status": "ONLINE",
        "districts": districts_list
    }

    with open(FEED_JSON, 'w', encoding='utf-8') as f:
        json.dump(updated_feed, f, ensure_ascii=False, indent=2)

    if has_changes:
        print(f"[✓] SUCCESS: Updated live_feed.json -> Events: {final_total_events:,} (+{final_total_events - current_events:,}), Reach: {final_total_reach:,}")
    else:
        print(f"[i] Feed already up to date with portal ({final_total_events:,} events). Timestamp refreshed.")

if __name__ == '__main__':
    sync_live()
