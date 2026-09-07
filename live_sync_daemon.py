#!/usr/bin/env python3
"""
Cyber Jagriti Abhiyan - Stealth Under-The-Radar Two-Tier Live Sync Daemon
Features:
- Tier 1: Ultra-Fast 5-8s Stealth Pulse (Fetches 2KB dashboard summary, updates live_feed.json instantly with zero lag)
- Tier 2: Deep 5-minute Batch Ingestion (Paginates new records into SQLite, backfills police stations, recompiles HTML, pushes to GitHub)
- Zero TLS Handshake Footprint (Persistent HTTP Keep-Alive session)
- Emulates native macOS Chrome Browser headers (Completely under the radar)
- Serves local dashboard & live_feed.json with CORS on port 8080
"""

import os
import sys
import time
import json
import random
import sqlite3
import argparse
import requests
import subprocess
from datetime import datetime

BASE_DIR = '/Users/abhijeet/.gemini/antigravity-ide/scratch/cyber-jagriti-monitor'
DB_PATH = os.path.join(BASE_DIR, 'events.db')
STATUS_FILE = os.path.join(BASE_DIR, 'live_sync_status.json')
FEED_JSON = os.path.join(BASE_DIR, 'live_feed.json')
INDEX_HTML = os.path.join(BASE_DIR, 'index.html')
MAP_GENERATOR_SCRIPT = os.path.join(BASE_DIR, 'generate_geospatial_map.py')
BACKFILL_SCRIPT = os.path.join(BASE_DIR, 'backfill_districts.py')
AUTH_CACHE_FILE = os.path.join(BASE_DIR, '.auth_cache.json')

# Stealth Chrome Browser Headers
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

def get_stealth_session():
    session = requests.Session()
    session.headers.update(CHROME_HEADERS)
    return session

def get_auth_token(session):
    if os.path.exists(AUTH_CACHE_FILE):
        try:
            with open(AUTH_CACHE_FILE, 'r') as f:
                cached = json.load(f)
                if time.time() - cached.get('timestamp', 0) < 14400:
                    token = cached.get('token')
                    test_headers = {"Authorization": token}
                    r = session.get("https://cyberjagriti.policemitanrpr.com/api/cyber_crime/dashboard", headers=test_headers, timeout=8)
                    if r.status_code == 200:
                        return token
        except:
            pass

    login_url = "https://cyberjagriti.policemitanrpr.com/api/login/check"
    r = session.post(login_url, json={"username": "admin", "***REMOVED***": "***REMOVED***"}, timeout=10)
    token = r.json().get("token")
    if token:
        with open(AUTH_CACHE_FILE, 'w') as f:
            json.dump({"token": token, "timestamp": time.time()}, f)
    return token

def fast_pulse_check(session, token, last_feed_events):
    """
    Tier 1: Lightweight 2KB dashboard pulse check.
    Takes ~150ms. If counter changed, updates live_feed.json immediately.
    """
    dash_url = "https://cyberjagriti.policemitanrpr.com/api/cyber_crime/dashboard"
    try:
        r = session.get(dash_url, headers={"Authorization": token}, timeout=8)
        if r.status_code != 200:
            return None, last_feed_events
        data = r.json()
    except Exception as e:
        return None, last_feed_events

    counter = data.get("counter", {})
    remote_total = int(counter.get("total_entries", 0))
    remote_reach = int(counter.get("total_members", 0))
    if remote_total == 0:
        return None, last_feed_events

    if remote_total != last_feed_events:
        delta = remote_total - last_feed_events
        avg_att = round(remote_reach / remote_total, 1) if remote_total > 0 else 0

        # Load existing feed to update top-level metrics while keeping district structure
        feed_data = {}
        if os.path.exists(FEED_JSON):
            try:
                with open(FEED_JSON, 'r', encoding='utf-8') as f:
                    feed_data = json.load(f)
            except:
                pass

        feed_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        feed_data["total_events"] = remote_total
        feed_data["total_reach"] = remote_reach
        feed_data["avg_attendance"] = avg_att
        feed_data["status"] = "LIVE_PULSE"

        # Update district entries accurately
        remote_districts = data.get("districts", [])
        if remote_districts:
            portal_by_id = {int(d.get("district_id", 0)): d for d in remote_districts}
            portal_by_name = {d.get("district_name_en", "").lower().strip(): d for d in remote_districts}

            # Raipur combined (Commissionerate 27 + Gramin 34)
            raipur_events = 0
            raipur_reach = 0
            for r_id in [27, 34]:
                if r_id in portal_by_id:
                    raipur_events += int(portal_by_id[r_id].get("total", 0))
                    raipur_reach += int(portal_by_id[r_id].get("total_members", 0))

            if "districts" in feed_data and feed_data["districts"]:
                for d in feed_data["districts"]:
                    did = int(d.get("id", 0))
                    name_clean = d.get("name_en", "").lower().strip()
                    if did == 27 or "raipur" in name_clean:
                        d["id"] = 27
                        d["events"] = raipur_events
                        d["reach"] = raipur_reach
                        d["avg_attendance"] = round(raipur_reach / raipur_events, 1) if raipur_events > 0 else 0
                    elif did in portal_by_id:
                        rd = portal_by_id[did]
                        d["events"] = int(rd.get("total", d.get("events", 0)))
                        d["reach"] = int(rd.get("total_members", d.get("reach", 0)))
                        d["avg_attendance"] = round(d["reach"] / d["events"], 1) if d["events"] > 0 else 0
                    elif name_clean in portal_by_name:
                        rd = portal_by_name[name_clean]
                        d["id"] = int(rd.get("district_id", did))
                        d["events"] = int(rd.get("total", d.get("events", 0)))
                        d["reach"] = int(rd.get("total_members", d.get("reach", 0)))
                        d["avg_attendance"] = round(d["reach"] / d["events"], 1) if d["events"] > 0 else 0

                feed_data["districts"].sort(key=lambda x: x.get("events", 0), reverse=True)
                for idx, d in enumerate(feed_data["districts"], 1):
                    d["rank"] = idx

        with open(FEED_JSON, 'w', encoding='utf-8') as f:
            json.dump(feed_data, f, ensure_ascii=False, indent=2)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] [FAST PULSE] Remote: {remote_total:,} (+{delta} new) | Reach: {remote_reach:,} -> live_feed.json updated!", flush=True)
        return remote_total, remote_total

    return remote_total, last_feed_events

def deep_event_ingestion(session, token, verbose=True):
    """
    Tier 2: Detailed batch event ingestion into SQLite events.db.
    Runs every 5 minutes or when delta threshold is reached.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), MAX(id) FROM events")
    local_count, local_max_id = cur.fetchone()
    local_max_id = local_max_id or 0

    list_url = "https://cyberjagriti.policemitanrpr.com/api/cyber_crime/list?page=1&limit=1"
    try:
        lr = session.get(list_url, headers={"Authorization": token}, timeout=10)
        latest_items = lr.json().get("result", [])
        portal_max_id = int(latest_items[0].get("id")) if latest_items else 0
    except Exception as e:
        conn.close()
        return 0

    if portal_max_id <= local_max_id:
        conn.close()
        return 0

    if verbose:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [DEEP SYNC] Ingesting delta events (Local Max ID: {local_max_id} -> Portal Max ID: {portal_max_id})...", flush=True)

    cur.execute("SELECT id FROM events ORDER BY id DESC LIMIT 5000")
    existing_ids = set([r[0] for r in cur.fetchall()])

    new_records = []
    page = 1
    consecutive_existing = 0
    while page <= 15:
        page_url = f"https://cyberjagriti.policemitanrpr.com/api/cyber_crime/list?page={page}&limit=500"
        try:
            lr = session.get(page_url, headers={"Authorization": token}, timeout=15)
            items = lr.json().get("result", [])
            if not items:
                break
        except:
            break

        stop = False
        for item in items:
            try:
                eid = int(item.get("id"))
            except:
                continue

            if eid in existing_ids:
                consecutive_existing += 1
                if consecutive_existing >= 25:
                    stop = True
                    break
                continue

            consecutive_existing = 0
            existing_ids.add(eid)

            members = 0
            try:
                members = int(item.get("total_members", 0) or 0)
            except:
                pass

            new_records.append((
                eid,
                item.get("police_station", ""),
                item.get("date", ""),
                item.get("time", ""),
                item.get("location", ""),
                item.get("photo_1", ""),
                item.get("photo_2", ""),
                item.get("photo_3", ""),
                item.get("photo_4", ""),
                item.get("photo_5", ""),
                item.get("pdf", ""),
                item.get("district_name_hi", ""),
                item.get("district_name_en", ""),
                item.get("created_at", ""),
                members,
                item.get("remarks", ""),
                item.get("cyber_topic", ""),
                int(item.get("week_id", 0)) if str(item.get("week_id", "")).isdigit() else 0,
                item.get("week_name", ""),
                item.get("topic", "")
            ))
        if stop:
            break
        page += 1

    if new_records:
        cur.executemany("INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", new_records)
        conn.commit()
        conn.close()

        # Run station backfill
        subprocess.run([sys.executable, BACKFILL_SCRIPT], cwd=BASE_DIR, capture_output=True)

        # Recompile dashboard
        subprocess.run([sys.executable, MAP_GENERATOR_SCRIPT], cwd=BASE_DIR, capture_output=True)

        if verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [DEEP SYNC] Ingested {len(new_records)} new events into SQLite & recompiled map.", flush=True)

        return len(new_records)

    conn.close()
    return 0

def git_push_batch(verbose=True):
    """
    Pushes recent updates to GitHub Pages repository.
    Runs every 3-5 minutes to avoid spamming git commits.
    """
    try:
        subprocess.run(["git", "add", "index.html", "chhattisgarh_cyber_jagriti_map.html", "live_feed.json"], cwd=BASE_DIR, check=True)
        # Check if diff exists
        diff = subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=BASE_DIR)
        if diff.returncode != 0:
            msg = f"Auto-sync live telemetry: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            subprocess.run(["git", "commit", "-m", msg], cwd=BASE_DIR, check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, check=True)
            if verbose:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [GIT PUSH] Deployed latest batch to GitHub Pages.", flush=True)
    except Exception as e:
        if verbose:
            print(f"[*] Git auto-push notice: {e}", flush=True)

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
            pass

    def serve():
        socketserver.TCPServer.allow_reuse_address = True
        try:
            with socketserver.TCPServer(("", port), CORSRequestHandler) as httpd:
                print(f"[*] Local Live Server running at: http://localhost:{port}/index.html", flush=True)
                httpd.serve_forever()
        except Exception as e:
            print(f"[*] Local server error on port {port}: {e}", flush=True)

    t = threading.Thread(target=serve, daemon=True)
    t.start()

def start_cloudflare_tunnel(port=8080):
    bin_path = os.path.join(BASE_DIR, "bin", "cloudflared")
    if not os.path.exists(bin_path):
        import shutil
        bin_path = shutil.which("cloudflared")
    if not bin_path or not os.path.exists(bin_path):
        print("[!] cloudflared binary not found in bin/ or PATH. Tunnel disabled.", flush=True)
        return None

    cmd = [bin_path, "tunnel", "--url", f"http://localhost:{port}"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    tunnel_url = None
    start_time = time.time()
    
    for line in iter(proc.stdout.readline, ''):
        if "trycloudflare.com" in line:
            import re
            m = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
            if m:
                tunnel_url = m.group(0)
                break
        if time.time() - start_time > 15:
            break
            
    if tunnel_url:
        print(f"[*] Cloudflare Live Edge Tunnel: {tunnel_url}/live_feed.json", flush=True)
        with open(os.path.join(BASE_DIR, "tunnel_url.txt"), "w") as f:
            f.write(tunnel_url)
    return tunnel_url

def run_two_tier_daemon(pulse_sec=6, deep_sync_sec=300, git_push_sec=300, serve_port=8080, enable_tunnel=False):
    print("="*68, flush=True)
    print("CYBER JAGRITI ABHIYAN - TWO-TIER UNDER-THE-RADAR LIVE SYNC DAEMON", flush=True)
    print(f"Tier 1 (Fast Pulse): Every {pulse_sec}s (2KB Dashboard Summary -> live_feed.json)", flush=True)
    print(f"Tier 2 (Deep Ingestion): Every {deep_sync_sec//60}m (Detailed Events -> SQLite & Recompile)", flush=True)
    print(f"Tier 3 (Cloud Deploy): Every {git_push_sec//60}m (Batch Push to GitHub Pages)", flush=True)
    print("Connection: Persistent HTTP Keep-Alive (Zero TLS Handshake Spikes)", flush=True)
    if serve_port:
        start_local_server(serve_port)
    if enable_tunnel and serve_port:
        start_cloudflare_tunnel(serve_port)
    print("="*68, flush=True)

    session = get_stealth_session()
    token = None

    last_feed_events = 0
    if os.path.exists(FEED_JSON):
        try:
            with open(FEED_JSON, 'r') as f:
                last_feed_events = json.load(f).get("total_events", 0)
        except:
            pass

    last_deep_sync = time.time()
    last_git_push = time.time()
    accumulated_delta = 0

    while True:
        try:
            if not token:
                token = get_auth_token(session)

            remote_total, last_feed_events = fast_pulse_check(session, token, last_feed_events)
            if remote_total:
                accumulated_delta = max(0, remote_total - last_feed_events)

            now = time.time()
            # Deep sync every 5 minutes OR if delta > 100
            if (now - last_deep_sync >= deep_sync_sec) or (accumulated_delta >= 100):
                ingested = deep_event_ingestion(session, token, verbose=True)
                last_deep_sync = now
                if ingested > 0:
                    accumulated_delta = 0

            # Git push every 5 minutes
            if now - last_git_push >= git_push_sec:
                git_push_batch(verbose=True)
                last_git_push = now

        except Exception as e:
            print(f"[*] Daemon cycle notice: {e}", flush=True)
            token = None # Refresh token on error

        # Small jitter on the 5-6s pulse so timing looks human/organic
        time.sleep(pulse_sec + random.uniform(0.5, 1.5))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Two-Tier Live Sync Daemon")
    parser.add_argument("--once", action="store_true", help="Run one-time sync and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuous two-tier daemon")
    parser.add_argument("--pulse", type=int, default=6, help="Pulse interval in seconds (default: 6s)")
    parser.add_argument("--deep", type=int, default=300, help="Deep sync interval in seconds (default: 300s / 5m)")
    parser.add_argument("--serve", type=int, nargs="?", const=8080, default=8080, help="Serve locally on port (default: 8080)")
    parser.add_argument("--tunnel", action="store_true", help="Spawn Cloudflare live edge tunnel for public 5s streaming")
    args = parser.parse_args()

    if args.once:
        session = get_stealth_session()
        token = get_auth_token(session)
        fast_pulse_check(session, token, 0)
        deep_event_ingestion(session, token, verbose=True)
        git_push_batch(verbose=True)
    elif args.daemon:
        run_two_tier_daemon(pulse_sec=args.pulse, deep_sync_sec=args.deep, git_push_sec=args.deep, serve_port=args.serve, enable_tunnel=args.tunnel)
    else:
        run_two_tier_daemon(pulse_sec=6, deep_sync_sec=300, git_push_sec=300, serve_port=8080, enable_tunnel=args.tunnel)
