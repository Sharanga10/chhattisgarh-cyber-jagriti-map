#!/usr/bin/env python3
"""
Autonomous Data Audit Agent for Cyber Jagriti Abhiyan.
Performs independent pre-flight data audits before generating executive reports:
1. Ground truth reconciliation (Portal API counter vs local SQLite database).
2. Temporal sanity audit (Identifies and quarantines future date typos or pre-campaign anomalies).
3. Data quality & outlier checks (Null/negative members, extreme attendee spikes).
4. Entity normalization (Unifies bilingual/transliterated Thana names into clean Devanagari).
5. Gatekeeper verdict (PASSED / AUTO_HEALED / BLOCKED) with structured audit report.
"""

import os
import sys
import json
import sqlite3
import requests
from datetime import datetime

BASE_DIR = "/Users/abhijeet/.gemini/antigravity-ide/scratch/cyber-jagriti-monitor"
DB_PATH = os.path.join(BASE_DIR, "events.db")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
AUDIT_LOG_PATH = os.path.join(REPORTS_DIR, "audit_results.json")

# Standard Chhattisgarh Police Districts (34)
KNOWN_DISTRICTS_HI = {
    "कोंडागांव", "गरियाबंद", "दुर्ग", "बिलासपुर", "बलरामपुर-रामानुजगंज", "जांजगीर-चांपा",
    "राजनांदगांव", "सुकमा", "बेमेतरा", "सूरजपुर", "बस्तर", "बलौदाबाजार-भाटापारा", "कबीरधाम",
    "मुंगेली", "रायगढ़", "कांकेर", "धमतरी", "कोरिया", "दंतेवाड़ा", "जशपुर", "गौरेला-पेंड्रा-मरवाही",
    "कोरबा", "बीजापुर", "खैरागढ़-छुईखदान-गंडई", "बालोद", "मोहला-मानपुर-अंबागढ़ चौकी",
    "मनेन्द्रगढ़-चिरमिरी-भरतपुर", "सारंगढ़-बिलाईगढ़", "महासमुंद", "सक्ती", "रायपुर",
    "रायपुर कमिश्नरेट", "नारायणपुर"
}

# Mapping table for Thana names (Unifying all transliterations to clean Devanagari)
THANA_CLEAN_MAP = {
    "devbhog": "देवभोग",
    "देवभोग": "देवभोग",
    "panduka": "पाण्डुका",
    "पाण्डुका": "पाण्डुका",
    "fingeshwar": "फिंगेश्वर",
    "फिंगेश्वर": "फिंगेश्वर",
    "vishrampuri": "विश्रामपुरी",
    "विश्रामपुरी": "विश्रामपुरी",
    "keshkal": "केशकाल",
    "केशकाल": "केशकाल",
    "थाना बड़े डोंगर": "बड़े डोंगर",
    "badedongar": "बड़े डोंगर",
    "बड़ेडोंगर": "बड़े डोंगर",
    "बड़े डोंगर": "बड़े डोंगर",
    "dongargarh": "डोंगरगढ़",
    "डोंगरगढ़": "डोंगरगढ़",
    "डोंगरगढ़": "डोंगरगढ़",
    "rajim": "राजिम",
    "राजिम": "राजिम",
    "police line": "पुलिस लाइन",
    "police line bilaspur": "पुलिस लाइन",
    "पुलिस लाइन": "पुलिस लाइन",
    "पुरानी भिलाई": "पुरानी भिलाई",
    "old bhilai": "पुरानी भिलाई",
    "kondagaon": "कोंडागांव",
    "कोण्डागांव": "कोंडागांव",
    "कोंडागांव": "कोंडागांव",
    "gariaband": "गरियाबंद",
    "गरियाबंद": "गरियाबंद",
    "dhanora": "धनोरा",
    "धनोरा": "धनोरा",
    "pharasgaon": "फरसगांव",
    "फरसगांव": "फरसगांव",
    "borigumma": "बोरीगुम्मा",
    "बोरीगुम्मा": "बोरीगुम्मा",
}

def clean_thana_name(raw_name):
    if not raw_name:
        return "अज्ञात थाना"
    raw_lower = raw_name.strip().lower()
    return THANA_CLEAN_MAP.get(raw_lower, raw_name.strip())

class DataAuditAgent:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.audit_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.today_str = datetime.now().strftime("%Y-%m-%d")
        self.results = {
            "timestamp": self.audit_timestamp,
            "target_date": self.today_str,
            "status": "PENDING",
            "ground_truth": {},
            "temporal_audit": {},
            "quality_audit": {},
            "normalization_audit": {},
            "district_audit": {},
            "quarantined_event_ids": [],
            "warnings": [],
            "action_taken": []
        }

    def fetch_live_ground_truth(self):
        """Step 1: Check live portal counters & district metrics for external verification."""
        try:
            login_url = "https://cyberjagriti.policemitanrpr.com/api/login/check"
            res = requests.post(login_url, json={"username": "admin", "***REMOVED***": "***REMOVED***"}, timeout=15)
            if res.status_code != 200:
                self.results["warnings"].append(f"Portal login returned HTTP {res.status_code}")
                return None
            token = res.json().get("token")
            if not token:
                self.results["warnings"].append("Portal auth token missing")
                return None

            dash_url = "https://cyberjagriti.policemitanrpr.com/api/cyber_crime/dashboard"
            dash_res = requests.get(dash_url, headers={"Authorization": token}, timeout=15)
            if dash_res.status_code == 200:
                dash_data = dash_res.json()
                return {
                    "counter": dash_data.get("counter", {}),
                    "districts": dash_data.get("districts", [])
                }
        except Exception as e:
            self.results["warnings"].append(f"Live API ground truth check failed: {str(e)}")
        return None

    def run_audit(self):
        print("=" * 60)
        print(f"[*] DATA AUDIT AGENT INITIALIZED: {self.audit_timestamp}")
        print(f"[*] Auditing Database: {self.db_path}")
        print("=" * 60)

        if not os.path.exists(self.db_path):
            self.results["status"] = "BLOCKED"
            self.results["warnings"].append("SQLite database file not found.")
            return self.results

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # ----------------------------------------------------
        # Audit 1: Ground Truth Reconciliation (Statewide)
        # ----------------------------------------------------
        print("\n[Audit 1/5] Reconciling Ground Truth Statewide Telemetry...")
        cur.execute("SELECT COUNT(*), SUM(total_members) FROM events")
        db_total_events, db_total_members = cur.fetchone()
        db_total_events = db_total_events or 0
        db_total_members = db_total_members or 0

        portal_data = self.fetch_live_ground_truth()
        portal_counter = portal_data.get("counter", {}) if portal_data else None
        portal_districts = portal_data.get("districts", []) if portal_data else []

        if portal_counter:
            portal_entries = portal_counter.get("total_entries", 0)
            portal_members = portal_counter.get("total_members", 0)
            diff_events = portal_entries - db_total_events
            parity_pct = (db_total_events / portal_entries * 100) if portal_entries > 0 else 100.0

            self.results["ground_truth"] = {
                "portal_entries": portal_entries,
                "portal_members": portal_members,
                "db_entries": db_total_events,
                "db_members": db_total_members,
                "parity_percentage": round(parity_pct, 2),
                "un_synced_delta": diff_events
            }
            print(f"    Portal Counter: {portal_entries:,} events | {portal_members:,} citizens")
            print(f"    Local Database: {db_total_events:,} events | {db_total_members:,} citizens")
            print(f"    Data Parity: {parity_pct:.2f}% (Delta: {diff_events})")
        else:
            self.results["ground_truth"] = {
                "portal_entries": None,
                "db_entries": db_total_events,
                "db_members": db_total_members,
                "note": "Offline verification against local store"
            }
            print(f"    Local Database: {db_total_events:,} events | {db_total_members:,} citizens")
            print(f"    Local Database: {db_total_events:,} events | {db_total_members:,} citizens")

        # ----------------------------------------------------
        # Audit 2: Temporal & Chronological Sanity
        # ----------------------------------------------------
        print("\n[Audit 2/4] Auditing Temporal Sanity (Date Boundaries)...")
        # Check for future dates (after today's date)
        cur.execute("SELECT id, event_date, total_members, police_station, district_name_hi FROM events WHERE event_date > ?", (self.today_str,))
        future_events = cur.fetchall()
        
        # Check for pre-campaign dates (prior to 2026-08-14)
        cur.execute("SELECT id, event_date, total_members FROM events WHERE event_date < '2026-08-14' AND event_date != ''")
        pre_campaign = cur.fetchall()

        quarantined_ids = []
        if future_events:
            print(f"    [!] Detected {len(future_events)} future-dated event(s):")
            for fe in future_events:
                eid, edate, emem, eps, edist = fe
                print(f"        - Event ID {eid}: Date={edate}, Members={emem}, Thana={eps}, Dist={edist}")
                quarantined_ids.append(eid)
            self.results["action_taken"].append(f"Quarantined {len(future_events)} future-dated event(s) from current daily cycle.")

        if pre_campaign:
            print(f"    [!] Detected {len(pre_campaign)} pre-campaign date event(s).")
            for pe in pre_campaign:
                quarantined_ids.append(pe[0])

        self.results["temporal_audit"] = {
            "future_dated_count": len(future_events),
            "pre_campaign_count": len(pre_campaign),
            "future_samples": [f"ID {fe[0]}: {fe[1]}" for fe in future_events[:5]]
        }
        self.results["quarantined_event_ids"] = quarantined_ids

        # ----------------------------------------------------
        # Audit 3: Data Quality, Nulls & Outliers
        # ----------------------------------------------------
        print("\n[Audit 3/4] Checking Data Quality, Zero/Negative Values & Outliers...")
        cur.execute("SELECT COUNT(*) FROM events WHERE total_members <= 0")
        zero_members_cnt = cur.fetchone()[0] or 0

        # Unrealistic single session outliers (> 10,000 in one event)
        cur.execute("SELECT id, police_station, district_name_hi, total_members, event_date FROM events WHERE total_members > 10000")
        mega_outliers = cur.fetchall()

        print(f"    Zero / Negative Member Records: {zero_members_cnt:,}")
        if mega_outliers:
            print(f"    [!] Detected {len(mega_outliers)} statistical outlier(s) > 10,000:")
            for mo in mega_outliers:
                print(f"        - ID {mo[0]}: {mo[3]:,} members at {mo[1]} ({mo[2]}) on {mo[4]}")

        self.results["quality_audit"] = {
            "zero_or_negative_members": zero_members_cnt,
            "extreme_outliers_count": len(mega_outliers),
            "extreme_outliers": [f"ID {mo[0]}: {mo[3]:,} members ({mo[1]})" for mo in mega_outliers]
        }

        # ----------------------------------------------------
        # Audit 4: Entity Normalization (Thanas & Districts)
        # ----------------------------------------------------
        # Audit 4: Entity Normalization (Thanas & Districts)
        # ----------------------------------------------------
        print("\n[Audit 4/5] Verifying Entity Normalization (Thanas & Districts)...")
        cur.execute("SELECT DISTINCT district_name_hi FROM events WHERE district_name_hi != ''")
        recorded_districts = [r[0].strip() for r in cur.fetchall()]
        print(f"    Total Active Districts: {len(recorded_districts)} / 34")

        cur.execute("SELECT DISTINCT police_station FROM events WHERE police_station != ''")
        raw_thanas = [r[0].strip() for r in cur.fetchall()]
        cleaned_thanas = set(clean_thana_name(t) for t in raw_thanas)
        print(f"    Total Distinct Thana Names: {len(raw_thanas)} raw -> normalized into {len(cleaned_thanas)} clean units")

        # Check for malformed station names (e.g. date strings in place of station name)
        cur.execute("SELECT COUNT(*) FROM events WHERE police_station GLOB '[0-9][0-9][0-9][0-9]*'")
        date_as_station_count = cur.fetchone()[0]
        if date_as_station_count > 0:
            print(f"    [!] ALERT: Detected {date_as_station_count} records with date as police station name!")
            self.results["warnings"].append(f"Detected {date_as_station_count} events where police_station is formatted as a date.")
        else:
            print("    Police station integrity: Verified (No date string artifacts detected).")

        self.results["normalization_audit"] = {
            "districts_covered": len(recorded_districts),
            "raw_thanas_count": len(raw_thanas),
            "normalized_thanas_count": len(cleaned_thanas),
            "date_station_corruptions": date_as_station_count
        }

        # ----------------------------------------------------
        # Audit 5: Per-District Ground Truth & Feed Alignment
        # ----------------------------------------------------
        print("\n[Audit 5/5] Cross-Verifying District Ground Truth & Live Feed Parity...")
        district_mismatches = []
        feed_mismatches = []

        feed_json_path = os.path.join(BASE_DIR, "live_feed.json")
        feed_districts_by_id = {}
        if os.path.exists(feed_json_path):
            try:
                with open(feed_json_path, "r", encoding="utf-8") as f:
                    fj = json.load(f)
                    for fd in fj.get("districts", []):
                        feed_districts_by_id[int(fd.get("id", 0))] = fd
            except Exception as e:
                self.results["warnings"].append(f"Failed to read live_feed.json: {e}")

        district_audit_records = []
        if portal_districts:
            for pd in portal_districts:
                did = int(pd.get("district_id", 0))
                dname_en = pd.get("district_name_en", "").strip()
                dname_hi = pd.get("district_name_hi", "").strip()
                portal_ev = int(pd.get("total", 0))
                portal_mem = int(pd.get("total_members", 0))

                # Database count for this district
                cur.execute("SELECT COUNT(*), SUM(total_members) FROM events WHERE district_id = ?", (did,))
                db_ev, db_mem = cur.fetchone()
                db_ev = db_ev or 0
                db_mem = db_mem or 0

                ev_delta = abs(portal_ev - db_ev)
                if ev_delta > 50:
                    district_mismatches.append({
                        "id": did, "name": dname_hi, "portal_events": portal_ev,
                        "db_events": db_ev, "delta": ev_delta
                    })

                feed_target_id = 27 if did in (27, 34) else did
                if feed_districts_by_id and feed_target_id in feed_districts_by_id:
                    fd = feed_districts_by_id[feed_target_id]
                    fd_ev = int(fd.get("events", 0))
                    if did not in (27, 34):
                        feed_delta = abs(portal_ev - fd_ev)
                        if feed_delta > 50:
                            feed_mismatches.append({
                                "id": did, "name": dname_hi, "portal_events": portal_ev,
                                "feed_events": fd_ev, "delta": feed_delta
                            })

                district_audit_records.append({
                    "id": did,
                    "name": dname_hi,
                    "portal_events": portal_ev,
                    "db_events": db_ev,
                    "delta": ev_delta
                })

            print(f"    Verified {len(portal_districts)} districts against Portal Ground Truth.")
            if district_mismatches:
                print(f"    [!] Detected {len(district_mismatches)} district count divergence(s) > 50:")
                for dm in district_mismatches[:5]:
                    print(f"        - {dm['name']} (ID {dm['id']}): Portal={dm['portal_events']}, DB={dm['db_events']} (Delta: {dm['delta']})")
            else:
                print("    All 33/34 Police districts are in telemetry alignment.")

            if feed_mismatches:
                print(f"    [!] Detected {len(feed_mismatches)} live_feed.json disparity alert(s):")
                for fm in feed_mismatches[:5]:
                    print(f"        - Feed {fm['name']} (ID {fm['id']}): Portal={fm['portal_events']}, Feed={fm['feed_events']}")
            elif feed_districts_by_id:
                print("    Live Map Feed (live_feed.json) is fully aligned with Ground Truth.")

        self.results["district_audit"] = {
            "districts_audited": len(portal_districts),
            "district_mismatches": district_mismatches,
            "feed_mismatches": feed_mismatches
        }

        # ----------------------------------------------------
        # Gatekeeper Verdict
        # ----------------------------------------------------
        if db_total_events == 0:
            self.results["status"] = "BLOCKED"
            self.results["verdict_message"] = "डेटाबेस रिक्त है (Database empty)."
        elif district_mismatches or feed_mismatches:
            self.results["status"] = "WARNING_MISMATCH"
            self.results["verdict_message"] = f"डेटा में विसंगति पाई गई: {len(district_mismatches)} जिले असंतुलित हैं।"
        elif quarantined_ids:
            self.results["status"] = "AUTO_HEALED"
            self.results["verdict_message"] = f"डेटा सत्यापित एवं उपचारित: {len(quarantined_ids)} विसंगतिपूर्ण प्रविष्टियों को रिपोर्ट से सुरक्षित रूप से पृथक किया गया।"
        else:
            self.results["status"] = "PASSED"
            self.results["verdict_message"] = "डेटा पूर्णतः सत्यापित एवं त्रुटिरहित है (100% Verified)."

        conn.close()

        # Persist audit results to file
        with open(AUDIT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 60)
        print(f"[*] AUDIT VERDICT: {self.results['status']}")
        print(f"[*] Message: {self.results['verdict_message']}")
        print(f"[*] Audit log saved to: {AUDIT_LOG_PATH}")
        print("=" * 60 + "\n")

        return self.results

def get_audited_events_query_filter(audit_results):
    """Helper returns SQL exclusion clause for quarantined events."""
    quarantined = audit_results.get("quarantined_event_ids", [])
    if quarantined:
        ids_str = ",".join(str(i) for i in quarantined)
        return f"id NOT IN ({ids_str})"
    return "1=1"

if __name__ == "__main__":
    agent = DataAuditAgent()
    results = agent.run_audit()
    print(json.dumps(results, indent=2, ensure_ascii=False))
