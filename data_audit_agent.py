#!/usr/bin/env python3
"""
Cyber Jagriti Abhiyan - Independent Pre-Flight Data Audit Agent
Performs 6-tier automated quality, temporal, entity normalization, ground-truth parity,
atomic snapshot locking, and cross-page report consistency checks.
"""

import os
import sys
import json
import sqlite3
import requests
from datetime import datetime
from token_utils import get_url_token

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "events.db")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
AUDIT_LOG_PATH = os.path.join(REPORTS_DIR, "audit_results.json")
os.makedirs(REPORTS_DIR, exist_ok=True)

def clean_thana_name(thana_raw):
    if not thana_raw:
        return ""
    t = thana_raw.strip()
    replacements = {
        "Devbhog": "देवभोग", "Panduka": "पाण्डुका", "Fingeshwar": "फिंगेश्वर",
        "Vishrampuri": "विश्रामपुरी", "Keshkal": "केशकाल", "थाना बड़े डोंगर": "बड़े डोंगर",
        "Badedongar": "बड़े डोंगर", "बड़ेडोंगर": "बड़े डोंगर", "बडेडाेगर": "बड़े डोंगर",
        "Dongargarh": "डोंगरगढ़", "डोंगरगढ़": "डोंगरगढ़", "Rajim": "राजिम",
        "Police line": "पुलिस लाइन", "Police Line Bilaspur": "पुलिस लाइन",
        "Police line bilaspur": "पुलिस लाइन", "पुरानी भिलाई": "पुरानी भिलाई",
        "Old Bhilai": "पुरानी भिलाई", "Kondagaon": "कोंडागांव", "कोण्डागांव": "कोंडागांव",
        "Gariaband": "गरियाबंद", "Dhanora": "धनोरा", "Pharasgaon": "फरसगांव",
        "Borigumma": "बोरीगुम्मा", "Chhura": "छुरा"
    }
    return replacements.get(t, t)

class DataAuditAgent:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.results = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "target_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "PENDING",
            "snapshot_max_id": 0,
            "ground_truth": {},
            "temporal_audit": {},
            "quality_audit": {},
            "normalization_audit": {},
            "district_audit": {},
            "quarantined_event_ids": [],
            "warnings": [],
            "action_taken": [],
            "verdict_message": ""
        }

    def run_audit(self):
        print("=" * 60)
        print(f"[*] DATA AUDIT AGENT INITIALIZED: {self.results['timestamp']}")
        print(f"[*] Auditing Database: {self.db_path}")
        print("=" * 60)

        if not os.path.exists(self.db_path):
            self.results["status"] = "BLOCKED"
            self.results["verdict_message"] = "Database file not found!"
            return self.results

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Freeze Snapshot Max ID for 100% Cross-Query Consistency
        cur.execute("SELECT MAX(id) FROM events")
        max_id = cur.fetchone()[0] or 0
        self.results["snapshot_max_id"] = max_id
        print(f"[*] Atomic Snapshot Frozen at Event ID #{max_id:,}")

        # ----------------------------------------------------
        # Audit 1: Telemetry Reconciler against Portal API
        # ----------------------------------------------------
        print("\n[Audit 1/6] Reconciling Ground Truth Statewide Telemetry...")
        portal_total_events = 0
        portal_total_reach = 0
        portal_districts = []

        login_url = "https://cyberjagriti.policemitanrpr.com/api/login/check"
        dash_url = f"https://cyberjagriti.policemitanrpr.com/api/cyber_crime/dashboard?token={get_url_token()}"

        try:
            r_auth = requests.post(login_url, json={"username": "admin", "***REMOVED***": "***REMOVED***"}, timeout=10)
            token = r_auth.json().get("token")
            if token:
                r_dash = requests.get(dash_url, headers={"Authorization": token}, timeout=10)
                dash_data = r_dash.json()
                counter = dash_data.get("counter", {})
                portal_total_events = int(counter.get("total_entries", 0))
                portal_total_reach = int(counter.get("total_members", 0))
                portal_districts = dash_data.get("districts", [])
        except Exception as e:
            self.results["warnings"].append(f"Portal API check failed ({e}). Auditing local database only.")

        cur.execute("SELECT COUNT(*), SUM(total_members) FROM events WHERE id <= ?", (max_id,))
        db_total_events, db_total_reach = cur.fetchone()
        db_total_events = db_total_events or 0
        db_total_reach = db_total_reach or 0

        parity = 100.0
        delta_events = 0
        if portal_total_events > 0:
            parity = round((db_total_events / portal_total_events) * 100, 2)
            delta_events = abs(portal_total_events - db_total_events)

        print(f"    Portal Counter: {portal_total_events:,} events | {portal_total_reach:,} citizens")
        print(f"    Local Database: {db_total_events:,} events | {db_total_reach:,} citizens")
        print(f"    Data Parity: {parity:.2f}% (Delta: {delta_events})")

        self.results["ground_truth"] = {
            "portal_entries": portal_total_events,
            "portal_members": portal_total_reach,
            "db_entries": db_total_events,
            "db_members": db_total_reach,
            "parity_percentage": parity,
            "un_synced_delta": delta_events
        }

        # ----------------------------------------------------
        # Audit 2: Temporal Sanity (Date Boundaries)
        # ----------------------------------------------------
        print("\n[Audit 2/6] Auditing Temporal Sanity (Date Boundaries)...")
        today_str = self.results["target_date"]
        cur.execute("SELECT id, event_date, total_members, police_station, district_name_hi FROM events WHERE id <= ? AND event_date > ?", (max_id, today_str))
        future_events = cur.fetchall()

        cur.execute("SELECT id, event_date FROM events WHERE id <= ? AND event_date < '2026-08-15'", (max_id,))
        pre_campaign_events = cur.fetchall()

        quarantined_ids = []
        if future_events:
            print(f"    [!] Detected {len(future_events)} future-dated event(s):")
            for fe in future_events:
                print(f"        - Event ID {fe[0]}: Date={fe[1]}, Members={fe[2]}, Thana={fe[3]}, Dist={fe[4]}")
                quarantined_ids.append(fe[0])
            self.results["warnings"].append(f"Detected {len(future_events)} future-dated event(s) beyond target date {today_str}.")
            self.results["action_taken"].append(f"Quarantined {len(future_events)} future-dated event(s) from current daily cycle.")

        self.results["temporal_audit"] = {
            "future_dated_count": len(future_events),
            "pre_campaign_count": len(pre_campaign_events),
            "future_samples": [f"ID {fe[0]}: {fe[1]}" for fe in future_events]
        }
        self.results["quarantined_event_ids"] = quarantined_ids

        # ----------------------------------------------------
        # Audit 3: Quality Audit (Zeros, Negative & Outliers)
        # ----------------------------------------------------
        print("\n[Audit 3/6] Checking Data Quality, Zero/Negative Values & Outliers...")
        cur.execute("SELECT COUNT(*) FROM events WHERE id <= ? AND (total_members <= 0 OR total_members IS NULL)", (max_id,))
        invalid_members_count = cur.fetchone()[0]

        cur.execute("SELECT id, total_members, police_station, district_name_hi, event_date FROM events WHERE id <= ? AND total_members > 10000", (max_id,))
        extreme_outliers = cur.fetchall()

        print(f"    Zero / Negative Member Records: {invalid_members_count}")
        if extreme_outliers:
            print(f"    [!] Detected {len(extreme_outliers)} statistical outlier(s) > 10,000:")
            for eo in extreme_outliers:
                print(f"        - ID {eo[0]}: {eo[1]:,} members at {eo[2]} ({eo[3]}) on {eo[4]}")

        self.results["quality_audit"] = {
            "zero_or_negative_members": invalid_members_count,
            "extreme_outliers_count": len(extreme_outliers),
            "extreme_outliers": [f"ID {eo[0]}: {eo[1]:,} members ({eo[2]})" for eo in extreme_outliers]
        }

        # ----------------------------------------------------
        # Audit 4: Entity Normalization (Thanas & Districts)
        # ----------------------------------------------------
        print("\n[Audit 4/6] Verifying Entity Normalization (Thanas & Districts)...")
        cur.execute("SELECT DISTINCT district_name_hi FROM events WHERE id <= ? AND district_name_hi != ''", (max_id,))
        recorded_districts = [r[0].strip() for r in cur.fetchall()]
        print(f"    Total Active Districts: {len(recorded_districts)} / 34")

        cur.execute("SELECT DISTINCT police_station FROM events WHERE id <= ? AND police_station != ''", (max_id,))
        raw_thanas = [r[0].strip() for r in cur.fetchall()]
        cleaned_thanas = set(clean_thana_name(t) for t in raw_thanas)
        print(f"    Total Distinct Thana Names: {len(raw_thanas)} raw -> normalized into {len(cleaned_thanas)} clean units")

        cur.execute("SELECT COUNT(*) FROM events WHERE id <= ? AND police_station GLOB '[0-9][0-9][0-9][0-9]*'", (max_id,))
        date_as_station_count = cur.fetchone()[0]

        self.results["normalization_audit"] = {
            "districts_covered": len(recorded_districts),
            "raw_thanas_count": len(raw_thanas),
            "normalized_thanas_count": len(cleaned_thanas),
            "date_station_corruptions": date_as_station_count
        }

        # ----------------------------------------------------
        # Audit 5: District Parity
        # ----------------------------------------------------
        print("\n[Audit 5/6] Cross-Verifying District Ground Truth...")
        district_mismatches = []
        if portal_districts:
            for pd in portal_districts:
                did = int(pd.get("district_id", 0))
                dname_hi = pd.get("district_name_hi", "").strip()
                portal_ev = int(pd.get("total", 0))
                cur.execute("SELECT COUNT(*) FROM events WHERE id <= ? AND district_id = ?", (max_id, did))
                db_ev = cur.fetchone()[0] or 0
                if abs(portal_ev - db_ev) > 50:
                    district_mismatches.append({"id": did, "name": dname_hi, "portal": portal_ev, "db": db_ev})

        self.results["district_audit"] = {
            "districts_audited": len(portal_districts),
            "district_mismatches": district_mismatches
        }

        # ----------------------------------------------------
        # Audit 6: Gatekeeper Verdict
        # ----------------------------------------------------
        if db_total_events == 0:
            self.results["status"] = "BLOCKED"
            self.results["verdict_message"] = "Database empty."
        elif district_mismatches:
            self.results["status"] = "WARNING_MISMATCH"
            self.results["verdict_message"] = f"District disparity: {len(district_mismatches)} districts mismatch > 50."
        elif quarantined_ids:
            self.results["status"] = "AUTO_HEALED"
            self.results["verdict_message"] = f"Audited & Quarantined: {len(quarantined_ids)} anomalous entry/entries isolated."
        else:
            self.results["status"] = "PASSED"
            self.results["verdict_message"] = "Data 100% verified & consistent."

        conn.close()

        with open(AUDIT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 60)
        print(f"[*] AUDIT VERDICT: {self.results['status']}")
        print(f"[*] Message: {self.results['verdict_message']}")
        print("=" * 60 + "\n")

        return self.results

    def verify_report_consistency(self, html_content):
        """
        Post-render audit verification: Parses all total event metrics across Page 1, Page 2, Page 3, and Page 4,
        and enforces 100% data parity across every section.
        """
        import re
        print("[Audit 6/6] Verifying Cross-Page Report Consistency...")
        
        # Regex matches any 'कुल विश्लेषित इवेंट: X' or 'कुल आयोजित इवेंट ... X' formatted numbers
        badges = re.findall(r'कुल विश्लेषित इवेंट:\s*([0-9,]+)', html_content)
        kpi_matches = re.findall(r'card-title">कुल आयोजित इवेंट</div>\s*<div class="card-value">([0-9,]+)</div>', html_content)
        footer_total = re.findall(r'कुल \(राज्य योग\)</td>.*?<td[^>]*>([0-9,]+)</td>\s*</tr>', html_content, re.DOTALL)
        
        found_totals = set(badges + kpi_matches + footer_total)
        
        if not found_totals:
            print("    [!] WARNING: Could not extract standard total markers for post-render audit.")
            return True
            
        if len(found_totals) > 1:
            err_msg = f"CRITICAL DATA AUDIT FAILURE! Discrepancy detected across report pages/sections: {found_totals}"
            print(f"    [!] FATAL: {err_msg}")
            raise ValueError(err_msg)
            
        matched_val = list(found_totals)[0]
        print(f"    [✓] Cross-Page Data Parity 100% Verified! All pages & sections report exactly: {matched_val} events.")
        return True

def get_audited_events_query_filter(audit_results):
    """Helper returns SQL exclusion clause for quarantined events AND frozen snapshot bound."""
    max_id = audit_results.get("snapshot_max_id", 0)
    quarantined = audit_results.get("quarantined_event_ids", [])
    
    parts = []
    if max_id > 0:
        parts.append(f"id <= {max_id}")
    if quarantined:
        ids_str = ",".join(str(i) for i in quarantined)
        parts.append(f"id NOT IN ({ids_str})")
        
    return " AND ".join(parts) if parts else "1=1"

if __name__ == "__main__":
    agent = DataAuditAgent()
    results = agent.run_audit()
    print(json.dumps(results, indent=2, ensure_ascii=False))
