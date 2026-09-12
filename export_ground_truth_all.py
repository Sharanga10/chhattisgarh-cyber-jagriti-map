#!/usr/bin/env python3
"""
Cyber Jagriti Abhiyan - Full Ground Truth Events Export (Day 1 to Yesterday)
Exports all 20 fields for all ingested events (187,966 records) to CSV (.csv) using standard library.
"""

import os
import sys
import sqlite3
import csv
import time

BASE_DIR = "/Users/abhi-macmini/.gemini/antigravity-ide/scratch/cyber-jagriti-monitor-repo"
DB_PATH = os.path.join(BASE_DIR, "events.db")
ARTIFACT_DIR = "/Users/abhi-macmini/.gemini/antigravity-ide/brain/6f59861b-1f45-4be1-a253-027ca122e4a4"

def export_ground_truth():
    print(f"[*] Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    query = """
    SELECT 
        id AS event_id,
        subject,
        police_station,
        district_id,
        district_name_en,
        CASE 
            WHEN district_id IN (27, 34) OR LOWER(district_name_en) LIKE '%raipur%' THEN 'रायपुर'
            WHEN district_name_hi IS NOT NULL AND district_name_hi != '' THEN district_name_hi
            ELSE district_name_en
        END AS district_name_hi,
        officer_name,
        designation,
        officer_contact_no,
        event_date,
        event_time,
        upload_datetime,
        village_name,
        panchayat_name,
        total_members,
        CASE 
            WHEN total_members >= 1 AND total_members <= 20 THEN '1-20'
            WHEN total_members >= 21 AND total_members <= 50 THEN '20-50'
            WHEN total_members >= 51 AND total_members <= 100 THEN '50-100'
            WHEN total_members >= 101 AND total_members <= 500 THEN '100-500'
            WHEN total_members > 500 THEN '>500'
            ELSE 'Unknown'
        END AS attendance_category,
        cyber_topic,
        week_name,
        topic,
        remarks
    FROM events
    WHERE event_date <= '2026-09-11'
    ORDER BY event_date ASC, id ASC
    """
    
    headers = [
        "Event ID",
        "Subject (विषय)",
        "Police Station (थाना)",
        "District ID",
        "District Name (English)",
        "District Name (Hindi / जिला)",
        "Officer / Incharge Name (अधिकारी का नाम)",
        "Designation (पद)",
        "Officer Contact (संपर्क नंबर)",
        "Event Date (दिनांक)",
        "Event Time (समय)",
        "Portal Upload Timestamp",
        "Village / Location (ग्राम/स्थान)",
        "Panchayat (पंचायत)",
        "Total Attendees (उपस्थिति/संख्या)",
        "Attendance Category (श्रेणी)",
        "Cyber Safety Topic (साइबर विषय)",
        "Campaign Week (सप्ताह)",
        "Topic Detail",
        "Remarks (टिप्पणी)"
    ]
    
    t0 = time.time()
    print("[1/2] Fetching all events from database...")
    cur.execute(query)
    rows = cur.fetchall()
    total_records = len(rows)
    print(f"[*] Retrieved {total_records:,} events in {time.time() - t0:.2f}s")
    
    csv_file = os.path.join(ARTIFACT_DIR, "Cyber_Jagriti_All_Events_Complete_Ground_Truth_2026-09-11.csv")
    
    t1 = time.time()
    print("[2/2] Writing UTF-8 with BOM CSV file for Excel...")
    with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
        
    csv_size_mb = os.path.getsize(csv_file) / (1024 * 1024)
    print(f"[*] CSV Export completed ({csv_size_mb:.2f} MB) in {time.time() - t1:.2f}s -> {csv_file}")
    print(f"\n✅ EXPORT SUCCESSFUL: All {total_records:,} events with all 20 fields exported!")

if __name__ == "__main__":
    export_ground_truth()
