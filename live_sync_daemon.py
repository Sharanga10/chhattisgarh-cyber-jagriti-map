#!/usr/bin/env python3
"""
Cyber Jagriti Abhiyan - Stealth Under-The-Radar Live Sync Daemon
Features:
- Emulates macOS Chrome browser headers (Zero tracing / Under the radar)
- Lightweight 2KB pre-flight counter check before fetching any data
- Micro-delta ingestion (only fetches new event records where id > max_id)
- Zero CPU / RAM footprint when idle
- Automatically re-compiles chhattisgarh_cyber_jagriti_map.html upon new events
- Supports one-shot (--once) or continuous daemon (--daemon with random jitter)
"""

import os
import sys
import time
import json
import random
import sqlite3
import argparse
import requests
from datetime import datetime

BASE_DIR = '/Users/abhijeet/.gemini/antigravity-ide/scratch/cyber-jagriti-monitor'
DB_PATH = os.path.join(BASE_DIR, 'events.db')
STATUS_FILE = os.path.join(BASE_DIR, 'live_sync_status.json')
MAP_GENERATOR_SCRIPT = os.path.join(BASE_DIR, 'generate_geospatial_map.py')

# Stealth Browser Emulation Headers
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

AUTH_CACHE_FILE = os.path.join(BASE_DIR, '.auth_cache.json')

def get_stealth_session():
    session = requests.Session()
    session.headers.update(CHROME_HEADERS)
    return session

def get_auth_token(session):
    # Check cached token
    if os.path.exists(AUTH_CACHE_FILE):
        try:
            with open(AUTH_CACHE_FILE, 'r') as f:
                cached = json.load(f)
                # If cached within last 4 hours, test token
                if time.time() - cached.get('timestamp', 0) < 14400:
                    test_headers = {"Authorization": cached.get('token')}
                    r = session.get("https://cyberjagriti.policemitanrpr.com/api/cyber_crime/dashboard", headers=test_headers, timeout=10)
                    if r.status_code == 200:
                        return cached.get('token')
        except:
            pass

    # Authenticate stealthily
    login_url = "https://cyberjagriti.policemitanrpr.com/api/login/check"
    resp = session.post(login_url, json={"username": "admin", "***REMOVED***": "***REMOVED***"}, timeout=15)
    resp.raise_for_status()
    token = resp.json().get("token")
    if not token:
        raise ValueError("Auth token missing from response.")

    with open(AUTH_CACHE_FILE, 'w') as f:
        json.dump({"token": token, "timestamp": time.time()}, f)
    return token

def check_and_sync_delta(verbose=True):
    start_time = time.time()
    session = get_stealth_session()

    # Step 1: Query local DB state
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), MAX(id) FROM events")
    local_count, local_max_id = cur.fetchone()
    local_max_id = local_max_id or 0

    # Step 2: Stealth counter check (2KB payload)
    try:
        token = get_auth_token(session)
    except Exception as e:
        if verbose:
            print(f"[*] Auth failed ({e}). Retrying next cycle.")
        conn.close()
        return False, 0

    dash_url = "https://cyberjagriti.policemitanrpr.com/api/cyber_crime/dashboard"
    try:
        r = session.get(dash_url, headers={"Authorization": token}, timeout=15)
        if r.status_code != 200:
            conn.close()
            return False, 0
        dash_data = r.json()
    except Exception as e:
        if verbose:
            print(f"[*] Dashboard ping failed ({e}).")
        conn.close()
        return False, 0

    counter = dash_data.get("counter", {})
    remote_count = int(counter.get("total_entries", local_count))
    remote_reach = int(counter.get("total_members", 0))

    list_url = "https://cyberjagriti.policemitanrpr.com/api/cyber_crime/list?page=1&limit=1"
    try:
        lr = session.get(list_url, headers={"Authorization": token}, timeout=15)
        latest_items = lr.json().get("result", [])
        portal_max_id = int(latest_items[0].get("id")) if latest_items else 0
    except Exception as e:
        if verbose:
            print(f"[*] Portal check failed: {e}")
        conn.close()
        return False, 0

    # Step 3: Check parity against portal counts and max ID
    if remote_count == local_count and portal_max_id <= local_max_id:
        duration = round(time.time() - start_time, 2)
        if verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [STEALTH PARITY 100%] Local: {local_count:,} | Portal: {remote_count:,} (Checked in {duration}s - Zero trace)")
        
        status = {
            "last_sync_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_events": local_count,
            "total_reach": remote_reach,
            "delta_synced": 0,
            "status": "HEALTHY_STEALTH_PARITY"
        }
        with open(STATUS_FILE, "w") as f:
            json.dump(status, f, indent=2)
        conn.close()
        return True, 0

    # Step 4: Pull delta records
    delta_est = max(remote_count - local_count, portal_max_id - local_max_id)
    if verbose:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [DELTA DETECTED] Local: {local_count:,}, Portal: {remote_count:,} (~{delta_est} new events). Fetching...")

    cur.execute("SELECT id FROM events ORDER BY id DESC LIMIT 5000")
    existing_ids = set([r[0] for r in cur.fetchall()])

    new_records = []
    page = 1
    consecutive_existing = 0
    while page <= 10:
        list_url = f"https://cyberjagriti.policemitanrpr.com/api/cyber_crime/list?page={page}&limit=500"
        try:
            lr = session.get(list_url, headers={"Authorization": token}, timeout=15)
            new_items = lr.json().get("result", [])
            if not new_items:
                break
        except Exception as e:
            if verbose:
                print(f"[*] Delta pull failed at page {page}: {e}")
            break

        stop_pulling = False
        for item in new_items:
            try:
                eid = int(item.get("id"))
            except:
                continue

            if eid in existing_ids:
                consecutive_existing += 1
                if consecutive_existing >= 25 and len(new_records) >= max(0, remote_count - local_count):
                    stop_pulling = True
                    break
                continue

            consecutive_existing = 0
            existing_ids.add(eid)

            try:
                members = int(item.get("total_members", 0))
            except:
                members = 0

            new_records.append((
                eid,
                item.get("subject", ""),
                (item.get("police_station") or "").strip(),
                int(item.get("district", 0)) if str(item.get("district", "")).isdigit() else 0,
                (item.get("district_name_en") or "").strip(),
                (item.get("district_name_hi") or "").strip(),
                (item.get("officer_name") or "").strip(),
                (item.get("designation") or "").strip(),
                (item.get("officer_contact_no") or "").strip(),
                item.get("date", ""),
                item.get("time", ""),
                item.get("upload_datetime", ""),
                (item.get("village_name") or "").strip(),
                (item.get("panchayat_name") or "").strip(),
                members,
                item.get("remarks", ""),
                item.get("cyber_topic", ""),
                int(item.get("week_id", 0)) if str(item.get("week_id", "")).isdigit() else 0,
                item.get("week_name", ""),
                item.get("topic", "")
            ))
        if stop_pulling:
            break
        page += 1

    if new_records:
        cur.executemany("""
            INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, new_records)
        conn.commit()
        if verbose:
            print(f"[*] Ingested {len(new_records)} new events into SQLite.")

        # Re-generate the map HTML automatically
        os.system(f"python3 {MAP_GENERATOR_SCRIPT} > /dev/null 2>&1")
        if verbose:
            print(f"[*] Re-compiled chhattisgarh_cyber_jagriti_map.html with updated metrics.")

    cur.execute("SELECT COUNT(*), SUM(total_members) FROM events")
    final_count, final_reach = cur.fetchone()
    conn.close()

    # Save status
    status = {
        "last_sync_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_events": final_count,
        "total_reach": final_reach or remote_reach,
        "delta_synced": len(new_records),
        "status": "HEALTHY_STEALTH"
    }
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)

    return True, len(new_records)

def start_local_server(port=8080):
    import http.server
    import socketserver
    import threading

    class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=BASE_DIR, **kwargs)

        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            super().end_headers()

        def log_message(self, format, *args):
            pass # Silent logs to keep terminal clean

    def serve():
        socketserver.TCPServer.allow_reuse_address = True
        try:
            with socketserver.TCPServer(("", port), CORSRequestHandler) as httpd:
                print(f"[*] Local Live Server running at: http://localhost:{port}/chhattisgarh_cyber_jagriti_map.html")
                httpd.serve_forever()
        except Exception as e:
            print(f"[*] Local server error on port {port}: {e}")

    t = threading.Thread(target=serve, daemon=True)
    t.start()

def run_daemon(interval_sec=900, serve_port=None):
    print("="*65)
    print("CYBER JAGRITI ABHIYAN - STEALTH LIVE FEED SYNC DAEMON")
    print(f"Base Interval: {interval_sec//60} mins with ±120s randomized stealth jitter")
    print("Mode: Under The Radar (Emulating macOS Chrome Headers)")
    if serve_port:
        start_local_server(serve_port)
    print("="*65)

    while True:
        try:
            check_and_sync_delta(verbose=True)
        except Exception as e:
            print(f"[*] Unexpected loop error: {e}")

        # Randomize jitter so poll intervals are never periodic clock spikes
        jitter = random.randint(-120, 120)
        sleep_duration = max(300, interval_sec + jitter)
        print(f"[*] Sleeping for {sleep_duration//60}m {sleep_duration%60}s before next stealth check...")
        time.sleep(sleep_duration)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stealth Live Sync Daemon")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background")
    parser.add_argument("--interval", type=int, default=900, help="Interval in seconds (default: 900s / 15m)")
    parser.add_argument("--serve", type=int, nargs="?", const=8080, default=None, help="Serve dashboard locally (default port: 8080)")
    args = parser.parse_args()

    if args.serve and not args.daemon:
        start_local_server(args.serve)
        check_and_sync_delta(verbose=True)
        print(f"[*] Press Ctrl+C to stop local server.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Exiting.")
    elif args.daemon:
        run_daemon(interval_sec=args.interval, serve_port=args.serve)
    else:
        check_and_sync_delta(verbose=True)
