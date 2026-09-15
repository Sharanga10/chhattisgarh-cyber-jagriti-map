import os
import sys
import time
import json
import sqlite3
import requests
import argparse
import random
import threading
import subprocess
from datetime import datetime
from token_utils import get_url_token

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEED_JSON = os.path.join(BASE_DIR, "live_feed.json")
DB_PATH = os.path.join(BASE_DIR, "events.db")
AUTH_CACHE_FILE = os.path.join(BASE_DIR, "auth_cache.json")
BACKFILL_SCRIPT = os.path.join(BASE_DIR, "backfill_districts.py")
MAP_GENERATOR_SCRIPT = os.path.join(BASE_DIR, "generate_geospatial_map.py")

CHROME_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

def init_db(conn):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY,
        subject TEXT,
        police_station TEXT,
        district_id INTEGER,
        district_name_en TEXT,
        district_name_hi TEXT,
        officer_name TEXT,
        designation TEXT,
        officer_contact_no TEXT,
        event_date TEXT,
        event_time TEXT,
        upload_datetime TEXT,
        village_name TEXT,
        panchayat_name TEXT,
        total_members INTEGER,
        remarks TEXT,
        cyber_topic TEXT,
        week_id INTEGER,
        week_name TEXT,
        topic TEXT
    )
    """)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM events")
    cnt = cur.fetchone()[0]
    csv_path = os.path.join(BASE_DIR, "cyber_jagriti_all_events.csv")
    if cnt < 100000 and os.path.exists(csv_path):
        import csv
        print(f"[*] Initializing SQLite DB from master CSV: {csv_path}...")
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            to_db = [(
                int(r.get('event_id') or r.get('id') or 0),
                r.get('subject', ''),
                r.get('police_station', ''),
                int(r.get('district_id', 0) or 0),
                r.get('district_name_en', ''),
                r.get('district_name_hi', ''),
                r.get('officer_name', ''),
                r.get('designation', ''),
                r.get('officer_contact_no', ''),
                r.get('event_date', ''),
                r.get('event_time', ''),
                r.get('upload_datetime', ''),
                r.get('village_name', ''),
                r.get('panchayat_name', ''),
                int(float(r.get('total_members', 0) or 0)),
                r.get('remarks', ''),
                r.get('cyber_topic', ''),
                int(r.get('week_id', 0) or 0),
                r.get('week_name', ''),
                r.get('topic', '')
            ) for r in reader if (r.get('event_id') or r.get('id'))]
            cur.executemany("INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", to_db)
            conn.commit()
            print(f"[✓] Initialized {len(to_db):,} events into events.db!")



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
                    r = session.get(f"https://cyberjagriti.policemitanrpr.com/api/cyber_crime/dashboard?token={get_url_token()}", headers=test_headers, timeout=8)
                    if r.status_code == 200:
                        return token
        except:
            pass

    login_url = "https://cyberjagriti.policemitanrpr.com/api/login/check"
    try:
        username = os.environ.get("CYBERJAGRITI_USER") or os.environ.get("CYBERJAGRITI_USERNAME")
        password = os.environ.get("CYBERJAGRITI_PASS") or os.environ.get("CYBERJAGRITI_PASSWORD")
        if not username or not password:
            cred_path = os.path.expanduser("~/.credentials/cyberjagriti.json")
            if os.path.exists(cred_path):
                try:
                    with open(cred_path, "r") as cf:
                        creds = json.load(cf)
                        username = username or creds.get("username")
                        password = password or creds.get("password")
                except Exception as ce:
                    print(f"[*] Notice reading external credentials: {ce}", flush=True)

        if not username or not password:
            print("[*] Live portal credentials not configured. Set CYBERJAGRITI_USERNAME and CYBERJAGRITI_PASSWORD.", flush=True)
            return None

        r = session.post(login_url, json={"username": username, "password": password}, timeout=10)
        token = r.json().get("token")
        if token:
            with open(AUTH_CACHE_FILE, 'w') as f:
                json.dump({"token": token, "timestamp": time.time()}, f)
        return token
    except Exception as e:
        print(f"[*] Live portal authentication notice: {e}", flush=True)
        return None

def fast_pulse_check(session, token, last_feed_events):
    """
    Tier 1: Lightweight 2KB dashboard pulse check.
    Takes ~150ms. If counter changed, updates live_feed.json immediately.
    """
    dash_url = f"https://cyberjagriti.policemitanrpr.com/api/cyber_crime/dashboard?token={get_url_token()}"
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

            # Keep portal IDs distinct. District 34 is a non-spatial card until
            # an authoritative boundary/centroid is available.
            existing_by_id = {int(d.get("id", 0)): d for d in feed_data.get("districts", [])}
            for did, rd in portal_by_id.items():
                if did == 0:
                    continue
                d = existing_by_id.get(did)
                if d is None:
                    d = {
                        "id": did,
                        "name_en": rd.get("district_name_en", ""),
                        "name_hi": rd.get("district_name_hi", ""),
                        "spatial": False,
                    }
                    feed_data.setdefault("districts", []).append(d)
                    existing_by_id[did] = d
                d["events"] = int(rd.get("total", d.get("events", 0)))
                d["reach"] = int(rd.get("total_members", d.get("reach", 0)))
                d["avg_attendance"] = round(d["reach"] / d["events"], 1) if d["events"] > 0 else 0

                feed_data["districts"].sort(key=lambda x: x.get("events", 0), reverse=True)
                for idx, d in enumerate(feed_data["districts"], 1):
                    d["rank"] = idx

        with open(FEED_JSON, 'w', encoding='utf-8') as f:
            json.dump(feed_data, f, ensure_ascii=False, indent=2)

        update_heartbeat("HEALTHY", remote_total, delta)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [FAST PULSE] Remote: {remote_total:,} (+{delta} new) | Reach: {remote_reach:,} -> live_feed.json updated!", flush=True)
        return remote_total, remote_total

    return remote_total, last_feed_events

def deep_event_ingestion(session, token, verbose=True):
    """
    Tier 2: Detailed batch event ingestion into SQLite events.db.
    Runs every 5 minutes or when delta threshold is reached.
    """
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), MAX(id) FROM events")
    local_count, local_max_id = cur.fetchone()
    local_max_id = local_max_id or 0

    if local_count == 0 or local_max_id == 0:
        conn.close()
        if verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [DEEP SYNC] Empty database detected. Performing initial baseline ingestion...", flush=True)
        from fetch_all_events import fetch_all
        saved = fetch_all(limit=5000)
        # Run station backfill & recompile map
        if os.path.exists(BACKFILL_SCRIPT):
            subprocess.run([sys.executable, BACKFILL_SCRIPT], cwd=BASE_DIR, capture_output=True)
        if os.path.exists(MAP_GENERATOR_SCRIPT):
            subprocess.run([sys.executable, MAP_GENERATOR_SCRIPT], cwd=BASE_DIR, capture_output=True)
        return saved

    list_url = f"https://cyberjagriti.policemitanrpr.com/api/cyber_crime/list?token={get_url_token()}&page=1&limit=1"
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
        page_url = f"https://cyberjagriti.policemitanrpr.com/api/cyber_crime/list?token={get_url_token()}&page={page}&limit=500"
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

            district_id = int(item.get("district", 0)) if str(item.get("district", "")).isdigit() else 0
            event_date = (item.get("date") or "").strip()
            try:
                event_day = datetime.strptime(event_date[:10], "%Y-%m-%d").date()
            except (TypeError, ValueError):
                continue
            if district_id == 0 or event_day > datetime.now().date():
                continue

            new_records.append((
                eid,
                item.get("subject", ""),
                (item.get("police_station") or "").strip(),
                district_id,
                (item.get("district_name_en") or "").strip(),
                (item.get("district_name_hi") or "").strip(),
                (item.get("officer_name") or "").strip(),
                (item.get("designation") or "").strip(),
                (item.get("officer_contact_no") or "").strip(),
                event_date,
                item.get("time", ""),
                item.get("date_time", ""),
                (item.get("village_name") or "").strip(),
                (item.get("panchayat_name") or "").strip(),
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
        cur.executemany("""
            INSERT OR REPLACE INTO events (
                id, subject, police_station, district_id, district_name_en, district_name_hi,
                officer_name, designation, officer_contact_no, event_date, event_time, upload_datetime,
                village_name, panchayat_name, total_members, remarks, cyber_topic, week_id, week_name, topic
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, new_records)
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

_git_push_lock = threading.Lock()
HEARTBEAT_FILE = os.path.join(BASE_DIR, "reports", "livesync_heartbeat.json")

def update_heartbeat(status="HEALTHY", last_events=0, delta=0):
    try:
        os.makedirs(os.path.dirname(HEARTBEAT_FILE), exist_ok=True)
        data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pid": os.getpid(),
            "status": status,
            "total_events": last_events,
            "recent_delta": delta
        }
        with open(HEARTBEAT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def _git_push_worker(verbose=True):
    if not _git_push_lock.acquire(blocking=False):
        if verbose:
            print("[*] Git push already running in background, skipping redundant trigger.", flush=True)
        return

    try:
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes -o ConnectTimeout=10"
        
        subprocess.run(["git", "add", "index.html", "chhattisgarh_cyber_jagriti_map.html", "live_feed.json"], cwd=BASE_DIR, check=True, timeout=15, env=env)
        diff = subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=BASE_DIR, timeout=10, env=env)
        if diff.returncode != 0:
            msg = f"Auto-sync live telemetry: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            subprocess.run(["git", "commit", "-m", msg], cwd=BASE_DIR, check=True, timeout=15, env=env)
            subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, check=True, timeout=30, env=env)
            if verbose:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [GIT PUSH] Deployed latest batch to GitHub Pages.", flush=True)
    except subprocess.TimeoutExpired:
        if verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [GIT PUSH] Warning: Git operation timed out (>30s) — aborted safely to avoid stalling sync.", flush=True)
    except Exception as e:
        if verbose:
            print(f"[*] Git auto-push notice: {e}", flush=True)
    finally:
        _git_push_lock.release()

def git_push_batch(verbose=True):
    """
    Pushes recent updates to GitHub Pages in a detached background thread.
    Strict 30s timeout and non-blocking lock ensure data ingestion NEVER stalls.
    """
    t = threading.Thread(target=_git_push_worker, args=(verbose,), daemon=True)
    t.start()

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
        conn = sqlite3.connect(DB_PATH)
        init_db(conn)
        conn.close()
        session = get_stealth_session()
        token = get_auth_token(session)
        if token:
            fast_pulse_check(session, token, 0)
            deep_event_ingestion(session, token, verbose=True)
        else:
            print("[*] Portal sync skipped (offline mode) — database successfully initialized.")
        git_push_batch(verbose=True)
    elif args.daemon:
        run_two_tier_daemon(pulse_sec=args.pulse, deep_sync_sec=args.deep, git_push_sec=args.deep, serve_port=args.serve, enable_tunnel=args.tunnel)
    else:
        run_two_tier_daemon(pulse_sec=6, deep_sync_sec=300, git_push_sec=300, serve_port=8080, enable_tunnel=args.tunnel)
