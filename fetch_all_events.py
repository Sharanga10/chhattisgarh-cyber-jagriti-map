#!/usr/bin/env python3
"""
Gentle, under-the-radar baseline fetcher for all Cyber Jagriti events.
Fetches in safe batches of 1,000 with a polite pause, storing into SQLite.
"""

import os
import sys
import time
import sqlite3
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "events.db")

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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_district ON events(district_name_en)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_thana ON events(police_station)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_date ON events(event_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_members ON events(total_members)")
    conn.commit()

def fetch_all():
    print("[*] Authenticating...")
    login_url = "https://cyberjagriti.policemitanrpr.com/api/login/check"
    res = requests.post(login_url, json={"username": "admin", "***REMOVED***": "***REMOVED***"}, timeout=30)
    token = res.json().get("token")
    if not token:
        print("Login failed!")
        return

    headers = {
        "Authorization": token,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
        "Referer": "https://cyberjagriti.policemitanrpr.com/admin/cybercrime",
        "Accept": "application/json, text/plain, */*"
    }

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    cur = conn.cursor()

    page = 1
    limit = 1000
    total_saved = 0
    total_records = None

    print("[*] Starting gentle batch retrieval (1,000 per request, 0.6s pause)...")
    while True:
        url = f"https://cyberjagriti.policemitanrpr.com/api/cyber_crime/list?page={page}&limit={limit}"
        try:
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code != 200:
                print(f"Error at page {page}: Status {r.status_code}")
                break
            data = r.json()
            if total_records is None:
                total_records = data.get("total_count", 0)
                print(f"[*] Total records reported by server: {total_records:,}")

            rows = data.get("result", [])
            if not rows:
                print(f"[*] No more rows returned at page {page}. Done.")
                break

            records_to_insert = []
            for item in rows:
                try:
                    eid = int(item.get("id"))
                except (ValueError, TypeError):
                    continue

                try:
                    members = int(item.get("total_members", 0))
                except (ValueError, TypeError):
                    members = 0

                records_to_insert.append((
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

            cur.executemany("""
                INSERT OR REPLACE INTO events (
                    id, subject, police_station, district_id, district_name_en, district_name_hi,
                    officer_name, designation, officer_contact_no, event_date, event_time, upload_datetime,
                    village_name, panchayat_name, total_members, remarks, cyber_topic, week_id, week_name, topic
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, records_to_insert)
            conn.commit()

            total_saved += len(records_to_insert)
            pct = (total_saved / total_records * 100) if total_records else 0
            print(f"  -> Page {page}: Saved {len(records_to_insert)} records | Cumulative: {total_saved:,}/{total_records:,} ({pct:.1f}%)")

            if len(rows) < limit:
                print("[*] Reached end of records.")
                break

            page += 1
            time.sleep(0.6) # polite 600ms delay to keep server load negligible
        except Exception as e:
            print(f"Exception on page {page}: {e}")
            time.sleep(2)
            continue

    conn.close()
    print(f"\n[+] Finished! Successfully stored {total_saved:,} events in {DB_PATH}")

if __name__ == "__main__":
    fetch_all()
