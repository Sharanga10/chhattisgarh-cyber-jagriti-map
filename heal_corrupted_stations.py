#!/usr/bin/env python3
"""
Auto-heals the corrupted events where police_station was accidentally populated with date.
Re-fetches accurate records from portal API and updates SQLite events table.
"""

import os
import sys
import json
import time
import sqlite3
import requests
from token_utils import get_url_token

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "events.db")
AUTH_CACHE = os.path.join(BASE_DIR, ".auth_cache.json")

def get_token():
    if os.path.exists(AUTH_CACHE):
        try:
            with open(AUTH_CACHE) as f:
                return json.load(f).get("token")
        except:
            pass
    r = requests.post("https://cyberjagriti.policemitanrpr.com/api/login/check", json={"username": "admin", "***REMOVED***": "***REMOVED***"}, timeout=15)
    return r.json().get("token")

def heal():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), MIN(id), MAX(id) FROM events WHERE police_station LIKE '2026-%'")
    corrupt_count, min_id, max_id = cur.fetchone()
    print(f"[*] Corrupted rows to heal: {corrupt_count:,} (ID range: {min_id} to {max_id})")

    token = get_token()
    if not token:
        print("[!] Failed to get auth token.")
        conn.close()
        return

    headers = {
        "Authorization": token,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    }

    session = requests.Session()
    session.headers.update(headers)

    page = 1
    total_repaired = 0
    min_target_id = (min_id or 83200) - 50

    while True:
        url = f"https://cyberjagriti.policemitanrpr.com/api/cyber_crime/list?token={get_url_token()}&page={page}&limit=500"
        try:
            r = session.get(url, timeout=20)
            if r.status_code != 200:
                print(f"[!] API returned status {r.status_code} at page {page}")
                break
            items = r.json().get("result", [])
            if not items:
                break
        except Exception as e:
            print(f"[!] Fetch error at page {page}: {e}")
            break

        records = []
        reached_end = False

        for item in items:
            try:
                eid = int(item.get("id"))
            except:
                continue

            if eid < min_target_id:
                reached_end = True
                break

            members = 0
            try:
                members = int(item.get("total_members", 0) or 0)
            except:
                pass

            records.append((
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

        if records:
            cur.executemany("""
                INSERT OR REPLACE INTO events (
                    id, subject, police_station, district_id, district_name_en, district_name_hi,
                    officer_name, designation, officer_contact_no, event_date, event_time, upload_datetime,
                    village_name, panchayat_name, total_members, remarks, cyber_topic, week_id, week_name, topic
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, records)
            conn.commit()
            total_repaired += len(records)
            print(f"[*] Page {page}: Repaired {len(records)} records (Current Page Min ID: {records[-1][0]}). Total so far: {total_repaired:,}")

        if reached_end:
            print("[*] Reached target ID boundary. Ingestion complete.")
            break

        page += 1
        time.sleep(0.15)

    cur.execute("SELECT COUNT(*) FROM events WHERE police_station LIKE '2026-%'")
    remaining = cur.fetchone()[0]
    print(f"[*] Done. Remaining corrupted rows: {remaining}")
    conn.close()

if __name__ == "__main__":
    heal()
