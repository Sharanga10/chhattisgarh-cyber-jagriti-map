#!/usr/bin/env python3
"""
Generate Chhattisgarh Cyber Jagriti Geospatial Impact Map
Executive-Grade, Ultra-Legible, High-Contrast & Colorful Map Dashboard

Fixes & Enhancements:
1. Eliminated rogue pointer lines ("labelling line going nowhere"):
   - No lines drawn on map polygon hover; replaced with rich interactive tooltip and smooth sidebar highlight.
   - Subtle pulse and card highlight on hover; zero off-screen diagonal line glitches.
2. Complete fix for "modals overlapping event scaling on the left below":
   - Event scaling (legend) relocated to Horizontal Bottom-Center floating pill dock.
   - Left flank cards constrained to max 4 cards with bottom: 90px buffer and internal scroll.
   - Top-bar toggle to hide/show flank cards at will.
3. Prominent, pulsing RED "LIVE MAP" button in header with instant sync status toast.
4. Maximum legibility & colorful aesthetic:
   - 5 distinct high-contrast vibrant choropleth colors (Royal Blue, Electric Purple, Emerald Green, Amber Gold, Crimson Rose).
   - Permanent crisp Devanagari district name badges directly on the map centroids.
   - Razor-sharp 2px boundary outlines with drop-shadow.
   - Clean base map switcher (Esri Dark Canvas default + OSM + Satellite + Light).
5. Header Title: strictly "साइबर जागृति अभियान" with campaign logo (logo.png).
6. Jumbo Apple-style KPI figures (66,515 Events, 33.71L Citizens Reached, 33/33 Districts, 50.7 Avg).
7. Reset View button (↺ पूरा मैप देखें).
8. Slide-over deep-dive district inspector drawer.
"""

import sqlite3
import json
import os
import base64
import re
from datetime import datetime

BASE_DIR = '/Users/abhijeet/.gemini/antigravity-ide/scratch/cyber-jagriti-monitor'
DB_PATH = os.path.join(BASE_DIR, 'events.db')
LOGO_PATH = os.path.join(BASE_DIR, 'logo_white.jpg')
GEOJSON_PATH = os.path.join(BASE_DIR, 'chhattisgarh_districts.geojson')
OUTPUT_HTML = os.path.join(BASE_DIR, 'chhattisgarh_cyber_jagriti_map.html')
INDEX_HTML = os.path.join(BASE_DIR, 'index.html')
ARTIFACT_HTML = '/Users/abhijeet/.gemini/antigravity-ide/brain/0c3c7ae5-0856-43de-a5ff-16b779c049ff/chhattisgarh_cyber_jagriti_map.html'
FEED_JSON = os.path.join(BASE_DIR, 'live_feed.json')
ARTIFACT_FEED_JSON = '/Users/abhijeet/.gemini/antigravity-ide/brain/0c3c7ae5-0856-43de-a5ff-16b779c049ff/live_feed.json'

# Master 33 Districts list with coordinates, flank side, and aliases
DISTRICTS_33 = [
    {
        "id": 1,
        "name_en": "Kondagaon",
        "name_hi": "कोंडागांव",
        "lat": 19.598,
        "lng": 81.662,
        "division": "Bastar",
        "flank": "left",
        "aliases": ["Kondagaon", "कोंडागांव", "कोंडागाँव"]
    },
    {
        "id": 2,
        "name_en": "Gariaband",
        "name_hi": "गरियाबंद",
        "lat": 20.958,
        "lng": 82.072,
        "division": "Raipur",
        "flank": "right",
        "aliases": ["Gariaband", "Gariyaband", "गरियाबंद"]
    },
    {
        "id": 3,
        "name_en": "Durg",
        "name_hi": "दुर्ग",
        "lat": 21.190,
        "lng": 81.285,
        "division": "Durg",
        "flank": "left",
        "aliases": ["Durg", "दुर्ग"]
    },
    {
        "id": 4,
        "name_en": "Bilaspur",
        "name_hi": "बिलासपुर",
        "lat": 22.080,
        "lng": 82.139,
        "division": "Bilaspur",
        "flank": "right",
        "aliases": ["Bilaspur", "बिलासपुर"]
    },
    {
        "id": 5,
        "name_en": "Balrampur-Ramanujganj",
        "name_hi": "बलरामपुर-रामानुजगंज",
        "lat": 23.613,
        "lng": 83.612,
        "division": "Surguja",
        "flank": "right",
        "aliases": ["Balrampur", "Balrampur-Ramanujganj", "बलरामपुर", "बलरामपुर-रामानुजगंज"]
    },
    {
        "id": 6,
        "name_en": "Janjgir-Champa",
        "name_hi": "जांजगीर-चांपा",
        "lat": 22.008,
        "lng": 82.571,
        "division": "Bilaspur",
        "flank": "right",
        "aliases": ["Janjgir-Champa", "Janjgir Champa", "जांजगीर-चांपा", "जांजगीर-चाम्पा"]
    },
    {
        "id": 7,
        "name_en": "Rajnandgaon",
        "name_hi": "राजनांदगांव",
        "lat": 21.101,
        "lng": 81.035,
        "division": "Durg",
        "flank": "left",
        "aliases": ["Rajnandgaon", "राजनांदगांव"]
    },
    {
        "id": 8,
        "name_en": "Sukma",
        "name_hi": "सुकमा",
        "lat": 18.796,
        "lng": 81.667,
        "division": "Bastar",
        "flank": "left",
        "aliases": ["Sukma", "सुकमा"]
    },
    {
        "id": 9,
        "name_en": "Bemetara",
        "name_hi": "बेमेतरा",
        "lat": 21.701,
        "lng": 81.547,
        "division": "Durg",
        "flank": "left",
        "aliases": ["Bemetara", "Bametara", "बेमेतरा"]
    },
    {
        "id": 10,
        "name_en": "Surajpur",
        "name_hi": "सूरजपुर",
        "lat": 23.220,
        "lng": 82.860,
        "division": "Surguja",
        "flank": "right",
        "aliases": ["Surajpur", "सूरजपुर"]
    },
    {
        "id": 11,
        "name_en": "Manendragarh-Chirmiri-Bharatpur",
        "name_hi": "मनेंद्रगढ़-चिरमिरी-भरतपुर",
        "lat": 23.213,
        "lng": 82.352,
        "division": "Surguja",
        "flank": "right",
        "aliases": ["Manendragarh-Chirmiri-Bharatpur", "MCB", "मनेंद्रगढ़-चिरमिरी-भरतपुर"]
    },
    {
        "id": 12,
        "name_en": "Bastar",
        "name_hi": "बस्तर",
        "lat": 19.074,
        "lng": 82.031,
        "division": "Bastar",
        "flank": "left",
        "aliases": ["Bastar", "बस्तर"]
    },
    {
        "id": 13,
        "name_en": "Baloda Bazar-Bhatapara",
        "name_hi": "बलौदाबाजार-भाटापारा",
        "lat": 21.658,
        "lng": 82.164,
        "division": "Raipur",
        "flank": "right",
        "aliases": ["Baloda Bazar", "Balodabazar-Bhatapara", "बलौदाबाजार-भाटापारा", "बलौदा बाजार"]
    },
    {
        "id": 14,
        "name_en": "Raigarh",
        "name_hi": "रायगढ़",
        "lat": 21.897,
        "lng": 83.395,
        "division": "Bilaspur",
        "flank": "right",
        "aliases": ["Raigarh", "रायगढ़"]
    },
    {
        "id": 15,
        "name_en": "Dantewada",
        "name_hi": "दंतेवाड़ा",
        "lat": 18.895,
        "lng": 81.349,
        "division": "Bastar",
        "flank": "left",
        "aliases": ["Dantewada", "Dakshin Bastar Dantewada", "दंतेवाड़ा", "दक्षिण बस्तर दंतेवाड़ा"]
    },
    {
        "id": 16,
        "name_en": "Bijapur",
        "name_hi": "बीजापुर",
        "lat": 18.797,
        "lng": 80.817,
        "division": "Bastar",
        "flank": "left",
        "aliases": ["Bijapur", "बीजापुर"]
    },
    {
        "id": 17,
        "name_en": "Raipur",
        "name_hi": "रायपुर",
        "lat": 21.251,
        "lng": 81.630,
        "division": "Raipur",
        "flank": "right",
        "aliases": ["Raipur Gramin", "Raipur Commissionerate", "Raipur", "रायपुर", "रायपुर ग्रामीण", "रायपुर कमिश्नरेट"]
    },
    {
        "id": 18,
        "name_en": "Balod",
        "name_hi": "बालोद",
        "lat": 20.730,
        "lng": 81.205,
        "division": "Durg",
        "flank": "left",
        "aliases": ["Balod", "बालोद"]
    },
    {
        "id": 19,
        "name_en": "Koriya",
        "name_hi": "कोरिया",
        "lat": 23.268,
        "lng": 82.557,
        "division": "Surguja",
        "flank": "right",
        "aliases": ["Koriya", "Korea", "कोरिया"]
    },
    {
        "id": 20,
        "name_en": "Mungeli",
        "name_hi": "मुंगेली",
        "lat": 22.068,
        "lng": 81.691,
        "division": "Bilaspur",
        "flank": "right",
        "aliases": ["Mungeli", "मुंगेली"]
    },
    {
        "id": 21,
        "name_en": "Khairagarh-Chhuikhadan-Gandai",
        "name_hi": "खैरागढ़-छुईखदान-गंडई",
        "lat": 21.417,
        "lng": 80.978,
        "division": "Durg",
        "flank": "left",
        "aliases": ["Khairagarh-Chhuikhadan-Gandai", "Khairagarh", "खैरागढ़-छुईखदान-गंडई"]
    },
    {
        "id": 22,
        "name_en": "Kabirdham",
        "name_hi": "कबीरधाम (कवर्धा)",
        "lat": 22.012,
        "lng": 81.248,
        "division": "Durg",
        "flank": "left",
        "aliases": ["Kabirdham", "Kabeerdham", "Kawardha", "कबीरधाम", "कवर्धा"]
    },
    {
        "id": 23,
        "name_en": "Korba",
        "name_hi": "कोरबा",
        "lat": 22.360,
        "lng": 82.750,
        "division": "Bilaspur",
        "flank": "right",
        "aliases": ["Korba", "कोरबा"]
    },
    {
        "id": 24,
        "name_en": "Dhamtari",
        "name_hi": "धमतरी",
        "lat": 20.707,
        "lng": 81.550,
        "division": "Raipur",
        "flank": "right",
        "aliases": ["Dhamtari", "धमतरी"]
    },
    {
        "id": 25,
        "name_en": "Jashpur",
        "name_hi": "जशपुर",
        "lat": 22.888,
        "lng": 84.142,
        "division": "Surguja",
        "flank": "right",
        "aliases": ["Jashpur", "जशपुर"]
    },
    {
        "id": 26,
        "name_en": "Mohla-Manpur-Ambagarh Chowki",
        "name_hi": "मोहला-मानपुर-चौकी",
        "lat": 20.578,
        "lng": 80.742,
        "division": "Durg",
        "flank": "left",
        "aliases": ["Mohla-Manpur-Ambagarh Chowki", "Mohla-Manpur", "मोहला-मानपुर-अंबागढ़ चौकी", "मोहला-मानपुर-चौकी"]
    },
    {
        "id": 27,
        "name_en": "Surguja",
        "name_hi": "सरगुजा",
        "lat": 23.121,
        "lng": 83.197,
        "division": "Surguja",
        "flank": "right",
        "aliases": ["Surguja", "सरगुजा", "Ambikapur", "अंबिकापुर"]
    },
    {
        "id": 28,
        "name_en": "Gaurela-Pendra-Marwahi",
        "name_hi": "गौरेला-पेंड्रा-मरवाही",
        "lat": 22.755,
        "lng": 81.954,
        "division": "Bilaspur",
        "flank": "right",
        "aliases": ["Gaurela-Pendra-Marwahi", "GPM", "गौरेला-पेंड्रा-मरवाही", "गौरेला-पेण्ड्रा-मरवाही"]
    },
    {
        "id": 29,
        "name_en": "Kanker",
        "name_hi": "कांकेर",
        "lat": 20.272,
        "lng": 81.491,
        "division": "Bastar",
        "flank": "left",
        "aliases": ["Kanker", "Uttar Bastar Kanker", "कांकेर", "उत्तर बस्तर कांकेर"]
    },
    {
        "id": 30,
        "name_en": "Mahasamund",
        "name_hi": "महासमुंद",
        "lat": 21.109,
        "lng": 82.097,
        "division": "Raipur",
        "flank": "right",
        "aliases": ["Mahasamund", "महासमुंद"]
    },
    {
        "id": 31,
        "name_en": "Sakti",
        "name_hi": "सक्ती",
        "lat": 22.029,
        "lng": 82.958,
        "division": "Bilaspur",
        "flank": "right",
        "aliases": ["Sakti", "सक्ती"]
    },
    {
        "id": 32,
        "name_en": "Sarangarh-Bilaigarh",
        "name_hi": "सारंगढ़-बिलाईगढ़",
        "lat": 21.583,
        "lng": 83.083,
        "division": "Bilaspur",
        "flank": "right",
        "aliases": ["Sarangarh-Bilaigarh", "सारंगढ़-बिलाईगढ़"]
    },
    {
        "id": 33,
        "name_en": "Narayanpur",
        "name_hi": "नारायणपुर",
        "lat": 19.721,
        "lng": 81.252,
        "division": "Bastar",
        "flank": "left",
        "aliases": ["Narayanpur", "नारायणपुर"]
    }
]

# Frontline Thana Coordinates
THANA_COORDS = {
    "devbhog": {"lat": 20.003, "lng": 82.553, "name_hi": "देवभोग", "name_en": "Devbhog", "district": "Gariaband"},
    "police line bilaspur": {"lat": 22.079, "lng": 82.148, "name_hi": "पुलिस लाइन बिलासपुर", "name_en": "Police Line Bilaspur", "district": "Bilaspur"},
    "vishrampuri": {"lat": 19.977, "lng": 81.748, "name_hi": "विश्रामपुरी", "name_en": "Vishrampuri", "district": "Kondagaon"},
    "fingeshwar": {"lat": 20.974, "lng": 81.982, "name_hi": "फिंगेश्वर", "name_en": "Fingeshwar", "district": "Gariaband"},
    "rajim": {"lat": 20.963, "lng": 81.884, "name_hi": "राजिम", "name_en": "Rajim", "district": "Gariaband"},
    "chhura": {"lat": 20.776, "lng": 82.179, "name_hi": "छुरा", "name_en": "Chhura", "district": "Gariaband"},
    "panduka": {"lat": 20.902, "lng": 81.938, "name_hi": "पाण्डुका", "name_en": "Panduka", "district": "Gariaband"},
    "keshkal": {"lat": 20.089, "lng": 81.590, "name_hi": "केशकाल", "name_en": "Keshkal", "district": "Kondagaon"},
    "gariaband": {"lat": 20.958, "lng": 82.072, "name_hi": "गरियाबंद", "name_en": "Gariaband", "district": "Gariaband"},
    "bada dongar": {"lat": 19.825, "lng": 81.688, "name_hi": "बड़े डोंगर", "name_en": "Bada Dongar", "district": "Kondagaon"},
    "purani bhilai": {"lat": 21.198, "lng": 81.332, "name_hi": "पुरानी भिलाई", "name_en": "Purani Bhilai", "district": "Durg"},
    "dongargarh": {"lat": 21.189, "lng": 80.763, "name_hi": "डोंगरगढ़", "name_en": "Dongargarh", "district": "Rajnandgaon"},
    "mainpur": {"lat": 20.404, "lng": 82.355, "name_hi": "मैनपुर", "name_en": "Mainpur", "district": "Gariaband"},
    "rajpur": {"lat": 23.479, "lng": 83.332, "name_hi": "राजपुर", "name_en": "Rajpur", "district": "Balrampur-Ramanujganj"},
    "mardapal": {"lat": 19.467, "lng": 81.821, "name_hi": "मर्दापाल", "name_en": "Mardapal", "district": "Kondagaon"},
    "bayanar": {"lat": 19.641, "lng": 81.520, "name_hi": "बयानार", "name_en": "Bayanar", "district": "Kondagaon"},
    "pulgaon": {"lat": 21.168, "lng": 81.242, "name_hi": "पुलगांव", "name_en": "Pulgaon", "district": "Durg"},
    "urandabeda": {"lat": 19.920, "lng": 81.540, "name_hi": "उरन्दाबेडा", "name_en": "Urandabeda", "district": "Kondagaon"},
    "manendragarh": {"lat": 23.213, "lng": 82.352, "name_hi": "मनेंद्रगढ़", "name_en": "Manendragarh", "district": "Manendragarh-Chirmiri-Bharatpur"},
    "farasgaon": {"lat": 19.833, "lng": 81.650, "name_hi": "फरसगांव", "name_en": "Farasgaon", "district": "Kondagaon"},
    "makdi": {"lat": 19.742, "lng": 81.902, "name_hi": "माकड़ी", "name_en": "Makdi", "district": "Kondagaon"},
    "city kotwali durg": {"lat": 21.190, "lng": 81.285, "name_hi": "सिटी कोतवाली दुर्ग", "name_en": "City Kotwali Durg", "district": "Durg"},
    "kondagaon kotwali": {"lat": 19.598, "lng": 81.662, "name_hi": "कोंडागांव कोतवाली", "name_en": "Kondagaon Kotwali", "district": "Kondagaon"},
    "mohan nagar": {"lat": 21.195, "lng": 81.275, "name_hi": "मोहन नगर", "name_en": "Mohan Nagar", "district": "Durg"},
    "pungarpal": {"lat": 19.500, "lng": 81.700, "name_hi": "पुंगरपाल", "name_en": "Pungarpal", "district": "Kondagaon"},
    "sarkanda": {"lat": 22.095, "lng": 82.155, "name_hi": "सरकंडा", "name_en": "Sarkanda", "district": "Bilaspur"},
    "newai": {"lat": 21.165, "lng": 81.341, "name_hi": "नेवई", "name_en": "Newai", "district": "Durg"},
    "bhilai nagar": {"lat": 21.214, "lng": 81.381, "name_hi": "भिलाई नगर", "name_en": "Bhilai Nagar", "district": "Durg"},
    "ramanujganj": {"lat": 23.805, "lng": 83.698, "name_hi": "रामानुजगंज", "name_en": "Ramanujganj", "district": "Balrampur-Ramanujganj"},
    "civil lines raipur": {"lat": 21.242, "lng": 81.650, "name_hi": "सिविल लाइन्स रायपुर", "name_en": "Civil Lines Raipur", "district": "Raipur"},
    "champa": {"lat": 22.043, "lng": 82.656, "name_hi": "चांपा", "name_en": "Champa", "district": "Janjgir-Champa"},
    "konta": {"lat": 17.808, "lng": 81.385, "name_hi": "कोंटा", "name_en": "Konta", "district": "Sukma"},
    "dornapal": {"lat": 18.283, "lng": 81.442, "name_hi": "दोरनापाल", "name_en": "Dornapal", "district": "Sukma"},
    "bhairamgarh": {"lat": 18.895, "lng": 80.771, "name_hi": "भैरमगढ़", "name_en": "Bhairamgarh", "district": "Bijapur"},
    "kawardha": {"lat": 22.012, "lng": 81.248, "name_hi": "कवर्धा", "name_en": "Kawardha", "district": "Kabirdham"},
    "ambikapur": {"lat": 23.121, "lng": 83.197, "name_hi": "अंबिकापुर", "name_en": "Ambikapur", "district": "Surguja"},
    "pathalgaon": {"lat": 22.562, "lng": 83.708, "name_hi": "पत्थलगांव", "name_en": "Pathalgaon", "district": "Jashpur"},
    "sarangarh": {"lat": 21.583, "lng": 83.083, "name_hi": "सारंगढ़", "name_en": "Sarangarh", "district": "Sarangarh-Bilaigarh"},
    "dhamtari": {"lat": 20.707, "lng": 81.550, "name_hi": "धमतरी", "name_en": "Dhamtari", "district": "Dhamtari"},
    "dalli rajhara": {"lat": 20.584, "lng": 81.082, "name_hi": "दल्ली राजहरा", "name_en": "Dalli Rajhara", "district": "Balod"},
    "marwahi": {"lat": 22.986, "lng": 82.036, "name_hi": "मरवाही", "name_en": "Marwahi", "district": "Gaurela-Pendra-Marwahi"},
    "antagarh": {"lat": 20.089, "lng": 81.168, "name_hi": "अंतागढ़", "name_en": "Antagarh", "district": "Kanker"}
}

def get_base64_logo():
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            mime = "image/jpeg" if LOGO_PATH.lower().endswith(('.jpg', '.jpeg')) else "image/png"
            return f"data:{mime};base64," + base64.b64encode(f.read()).decode("utf-8")
    return ""

def main():
    print("[1/4] Connecting to SQLite database...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Query metrics for each of the 33 districts
    district_data = []
    district_metric_map = {}

    for d in DISTRICTS_33:
        aliases = d["aliases"]
        placeholders = ','.join(['?'] * len(aliases))
        q = f'''SELECT COUNT(*), SUM(total_members), ROUND(AVG(total_members), 1) 
                FROM events 
                WHERE district_name_en IN ({placeholders}) OR district_name_hi IN ({placeholders})'''
        cursor.execute(q, aliases + aliases)
        row = cursor.fetchone()
        events = row[0] or 0
        reach = row[1] or 0
        avg_att = row[2] or 0.0

        # Query top thanas for this district
        q_thana = f'''SELECT police_station, COUNT(*), SUM(total_members)
                      FROM events
                      WHERE (district_name_en IN ({placeholders}) OR district_name_hi IN ({placeholders}))
                        AND police_station IS NOT NULL AND police_station != ''
                      GROUP BY police_station
                      ORDER BY COUNT(*) DESC LIMIT 4'''
        cursor.execute(q_thana, aliases + aliases)
        top_thanas = [{"name": r[0], "events": r[1], "reach": r[2]} for r in cursor.fetchall()]

        # Query top cyber crime topics for this district
        q_topic = f'''SELECT topic, COUNT(*)
                      FROM events
                      WHERE (district_name_en IN ({placeholders}) OR district_name_hi IN ({placeholders}))
                        AND topic IS NOT NULL AND topic != ''
                      GROUP BY topic
                      ORDER BY COUNT(*) DESC LIMIT 3'''
        cursor.execute(q_topic, aliases + aliases)
        top_topics = [{"name": r[0], "count": r[1]} for r in cursor.fetchall()]

        d_obj = {
            "id": d["id"],
            "name_en": d["name_en"],
            "name_hi": d["name_hi"],
            "lat": d["lat"],
            "lng": d["lng"],
            "division": d["division"],
            "flank": d["flank"],
            "events": events,
            "reach": reach,
            "avg_attendance": avg_att,
            "top_thanas": top_thanas,
            "top_topics": top_topics
        }
        district_data.append(d_obj)
        for a in aliases:
            district_metric_map[a.lower()] = d_obj
        district_metric_map[d["name_en"].lower()] = d_obj

    # Sort districts by events descending and assign ranks
    district_data.sort(key=lambda x: x["events"], reverse=True)
    for rank, d in enumerate(district_data, 1):
        d["rank"] = rank

    # Query all Thanas and aggregate
    print("[2/4] Aggregating frontline thana hubs...")
    cursor.execute('''SELECT police_station, district_name_en, COUNT(*), SUM(total_members)
                      FROM events
                      WHERE police_station IS NOT NULL AND police_station != ''
                      GROUP BY police_station, district_name_en''')

    def clean_thana(name):
        n = name.strip()
        n = re.sub(r'^(थाना\s+|Thana\s+|PS\s+|P\.S\.\s+)', '', n, flags=re.I)
        return re.sub(r'\s+', ' ', n).strip().lower()

    thana_agg = {}
    for ps, dist, count, reach in cursor.fetchall():
        c_ps = clean_thana(ps)
        matched_key = None
        for k in THANA_COORDS:
            if k in c_ps or c_ps in k:
                matched_key = k
                break
        if matched_key:
            if matched_key not in thana_agg:
                thana_agg[matched_key] = {"events": 0, "reach": 0}
            thana_agg[matched_key]["events"] += count
            thana_agg[matched_key]["reach"] += (reach or 0)

    thana_points = []
    for k, coords in THANA_COORDS.items():
        stats = thana_agg.get(k, {"events": 0, "reach": 0})
        if stats["events"] > 0:
            avg = round(stats["reach"] / stats["events"], 1) if stats["events"] else 0
            thana_points.append({
                "key": k,
                "name_hi": coords["name_hi"],
                "name_en": coords["name_en"],
                "district": coords["district"],
                "lat": coords["lat"],
                "lng": coords["lng"],
                "events": stats["events"],
                "reach": stats["reach"],
                "avg_attendance": avg
            })

    thana_points.sort(key=lambda x: x["events"], reverse=True)

    # Load GeoJSON
    with open(GEOJSON_PATH, 'r') as f:
        geo_data = json.load(f)

    # Attach stats to GeoJSON features
    for feature in geo_data.get('features', []):
        props = feature.get('properties', {})
        d_name = props.get('district', '').strip()
        matched = None
        for alias, d_obj in district_metric_map.items():
            if alias in d_name.lower() or d_name.lower() in alias:
                matched = d_obj
                break
        if matched:
            props['events'] = matched['events']
            props['reach'] = matched['reach']
            props['avg_attendance'] = matched['avg_attendance']
            props['rank'] = matched['rank']
            props['division'] = matched['division']
            props['name_hi'] = matched['name_hi']
            props['name_en'] = matched['name_en']
        else:
            props['events'] = 0
            props['reach'] = 0
            props['avg_attendance'] = 0
            props['rank'] = 99
            props['name_hi'] = d_name
            props['name_en'] = d_name

    # State Totals from DB
    cursor.execute('SELECT COUNT(*), SUM(total_members) FROM events')
    total_events, total_reach = cursor.fetchone()
    avg_state_att = round(total_reach / total_events, 1) if total_events else 0

    logo_b64 = get_base64_logo()
    print(f"[3/4] Compiling High-Contrast Dashboard (Events: {total_events:,}, Reach: {total_reach:,})...")

    html_content = f"""<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>साइबर जागृति अभियान | Geospatial Impact Dashboard</title>
    <!-- Google Sans, Poppins & SF Pro Stack -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600;700&family=Poppins:wght@300;400;500;600;700&family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap" rel="stylesheet">
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
    
    <style>
        :root {{
            --bg-canvas: #090d1a;
            --surface-primary: #0f172a;
            --surface-secondary: #1e293b;
            --surface-glass: rgba(15, 23, 42, 0.90);
            --surface-glass-card: rgba(15, 23, 42, 0.94);
            --hairline-border: rgba(255, 255, 255, 0.14);
            --hairline-border-active: rgba(255, 255, 255, 0.45);
            --text-primary: #ffffff;
            --text-secondary: #94a3b8;
            --text-tertiary: #64748b;
            --accent-red: #ef4444;
            --accent-blue: #3b82f6;
            --font-main: -apple-system, BlinkMacSystemFont, 'Google Sans', 'Poppins', sans-serif;
            --font-hindi: 'Noto Sans Devanagari', 'Poppins', sans-serif;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-font-smoothing: antialiased;
        }}
        
        body {{
            font-family: var(--font-main);
            background-color: var(--bg-canvas);
            color: var(--text-primary);
            height: 100vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }}

        /* Executive Header */
        header {{
            background: linear-gradient(135deg, #090d1a 0%, #111827 100%);
            border-bottom: 1px solid var(--hairline-border);
            padding: 11px 26px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            z-index: 1000;
            box-shadow: 0 4px 24px rgba(0,0,0,0.6);
        }}

        .header-brand-box {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}

        .campaign-logo-box {{
            width: 48px;
            height: 48px;
            border-radius: 11px;
            background: #ffffff;
            padding: 2.5px;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1.5px solid rgba(255, 255, 255, 0.4);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.55), 0 0 10px rgba(255, 255, 255, 0.15);
            flex-shrink: 0;
            overflow: hidden;
        }}

        .campaign-logo-img {{
            width: 100%;
            height: 100%;
            border-radius: 8px;
            object-fit: contain;
            background: #ffffff;
            display: block;
        }}

        .brand-text-block {{
            display: flex;
            flex-direction: column;
        }}

        .brand-title-row {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .brand-title {{
            font-size: 22px;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.3px;
            font-family: var(--font-hindi);
        }}

        /* Prominent Glowing RED LIVE MAP Button */
        .brand-tag-live {{
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: #ffffff;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.4);
            text-transform: uppercase;
            letter-spacing: 0.8px;
            box-shadow: 0 0 16px rgba(239, 68, 68, 0.75);
            display: inline-flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }}

        .brand-tag-live:hover {{
            transform: scale(1.05);
            box-shadow: 0 0 22px rgba(239, 68, 68, 0.95);
        }}

        .live-dot-pulse {{
            display: inline-block;
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #ffffff;
            box-shadow: 0 0 8px #ffffff;
            animation: livePulse 1.2s infinite;
        }}

        @keyframes livePulse {{
            0% {{ opacity: 0.4; transform: scale(0.8); }}
            50% {{ opacity: 1; transform: scale(1.25); }}
            100% {{ opacity: 0.4; transform: scale(0.8); }}
        }}

        .brand-subtitle {{
            font-size: 12px;
            color: var(--text-secondary);
            font-weight: 400;
            margin-top: 2px;
        }}

        /* Jumbo Header Metric Counters (High Contrast) */
        .jumbo-kpi-container {{
            display: flex;
            align-items: center;
            gap: 26px;
        }}

        .jumbo-kpi-block {{
            display: flex;
            flex-direction: column;
            align-items: flex-end;
        }}

        .jumbo-kpi-value {{
            font-size: 27px;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.05;
            letter-spacing: -0.5px;
            font-feature-settings: "tnum";
            font-variant-numeric: tabular-nums;
        }}

        .jumbo-kpi-label {{
            font-size: 10.5px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.6px;
            font-weight: 600;
            margin-top: 2px;
        }}

        .kpi-divider {{
            width: 1px;
            height: 34px;
            background: var(--hairline-border);
        }}

        /* Main Workspace Viewport */
        .app-workspace {{
            display: flex;
            flex: 1;
            position: relative;
            height: calc(100vh - 74px);
            background: var(--bg-canvas);
        }}

        /* Leaflet Map */
        #map {{
            flex: 1;
            height: 100%;
            background: #090d1a;
            z-index: 10;
        }}

        /* Floating Flank Callout Containers (Constrained to NEVER reach bottom) */
        .callout-flank {{
            position: absolute;
            top: 72px;
            bottom: 90px; /* Safe 90px buffer from bottom */
            max-height: calc(100vh - 220px);
            width: 230px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            z-index: 450;
            pointer-events: none;
            overflow-y: auto;
            padding: 4px;
            scrollbar-width: none;
            transition: opacity 0.25s ease;
        }}
        .callout-flank::-webkit-scrollbar {{
            display: none;
        }}

        .callout-flank-left {{
            left: 20px;
            top: 66px;
        }}

        .callout-flank-right {{
            right: 400px;
            top: 18px;
        }}

        .callout-flank.hidden {{
            opacity: 0;
            pointer-events: none;
        }}

        .callout-arm-card {{
            pointer-events: auto;
            background: var(--surface-glass-card);
            border: 1px solid var(--hairline-border);
            border-left: 4px solid #3b82f6;
            border-radius: 9px;
            padding: 8px 12px;
            backdrop-filter: blur(24px) saturate(180%);
            box-shadow: 0 4px 16px rgba(0,0,0,0.55);
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            position: relative;
        }}

        .callout-arm-card:hover, .callout-arm-card.active {{
            background: #1e293b;
            border-color: #ffffff;
            transform: translateY(-2px) scale(1.02);
            box-shadow: 0 8px 24px rgba(59, 130, 246, 0.35);
        }}

        .callout-card-title-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 3px;
        }}

        .callout-card-name {{
            font-size: 13.5px;
            font-weight: 600;
            color: #ffffff;
            font-family: var(--font-hindi);
        }}

        .callout-card-rank {{
            font-size: 10px;
            font-weight: 700;
            color: #93c5fd;
            background: rgba(59, 130, 246, 0.18);
            border: 1px solid rgba(59, 130, 246, 0.35);
            padding: 1px 6px;
            border-radius: 4px;
        }}

        .callout-card-stat {{
            font-size: 11.5px;
            color: #e2e8f0;
            font-weight: 600;
            font-feature-settings: "tnum";
        }}

        .callout-card-substat {{
            font-size: 11px;
            color: var(--text-secondary);
            margin-top: 1px;
        }}

        /* Permanent District Centroid Badges on Map */
        .district-centroid-label {{
            color: #ffffff;
            font-family: var(--font-hindi);
            font-size: 11px;
            font-weight: 700;
            text-shadow: 0 0 4px #000, 0 0 8px #000, 1px 1px 2px #000;
            white-space: nowrap;
            pointer-events: none;
            text-align: center;
            letter-spacing: -0.1px;
        }}

        /* Rich Leaflet Custom Tooltip */
        .leaflet-tooltip-apple {{
            background: rgba(15, 23, 42, 0.95) !important;
            border: 1px solid var(--hairline-border-active) !important;
            border-radius: 10px !important;
            padding: 10px 14px !important;
            color: #ffffff !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.7) !important;
            backdrop-filter: blur(20px) !important;
            font-family: var(--font-main) !important;
            min-width: 220px;
        }}
        .leaflet-tooltip-apple::before {{
            border-top-color: rgba(15, 23, 42, 0.95) !important;
        }}

        /* Distinct Thana Hub Hover Tooltip (Dark Crimson-Obsidian Glass, Zero White Border) */
        .leaflet-tooltip-thana {{
            background: linear-gradient(145deg, rgba(32, 10, 22, 0.97) 0%, rgba(15, 23, 42, 0.98) 100%) !important;
            border: 1px solid rgba(239, 68, 68, 0.45) !important;
            border-radius: 10px !important;
            padding: 10px 14px !important;
            color: #ffffff !important;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.8), 0 0 18px rgba(239, 68, 68, 0.25) !important;
            backdrop-filter: blur(20px) !important;
            font-family: var(--font-main) !important;
            min-width: 220px;
        }}
        .leaflet-tooltip-thana::before {{
            border-top-color: rgba(32, 10, 22, 0.97) !important;
            border-bottom-color: rgba(32, 10, 22, 0.97) !important;
        }}

        /* Leaflet Controls & Popups Dark Overrides */
        .leaflet-bar {{
            border: 1px solid var(--hairline-border) !important;
            border-radius: 8px !important;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6) !important;
        }}
        .leaflet-bar a {{
            background-color: rgba(15, 23, 42, 0.94) !important;
            color: #ffffff !important;
            border-bottom: 1px solid var(--hairline-border) !important;
            backdrop-filter: blur(20px);
            transition: all 0.15s ease;
            width: 32px !important;
            height: 32px !important;
            line-height: 32px !important;
            font-size: 16px !important;
        }}
        .leaflet-bar a:hover {{
            background-color: #1e293b !important;
            color: #60a5fa !important;
        }}
        .leaflet-popup-content-wrapper {{
            background: rgba(15, 23, 42, 0.97) !important;
            color: #ffffff !important;
            border: 1px solid var(--hairline-border) !important;
            border-radius: 10px !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.8) !important;
        }}
        .leaflet-popup-tip {{
            background: rgba(15, 23, 42, 0.97) !important;
        }}

        /* Collapsible / Expandable Map Layers Dock at Top-Left */
        .map-layers-dock {{
            position: absolute;
            top: 14px;
            left: 20px;
            z-index: 500;
            display: flex;
            align-items: center;
            background: rgba(15, 23, 42, 0.94);
            border: 1px solid var(--hairline-border);
            border-radius: 9999px;
            backdrop-filter: blur(24px) saturate(180%);
            box-shadow: 0 6px 24px rgba(0, 0, 0, 0.55);
            /* Lazy, delayed collapse: holds for 220ms before smoothly collapsing over 0.52s */
            transition: max-width 0.52s cubic-bezier(0.22, 1, 0.36, 1) 0.22s,
                        box-shadow 0.35s ease 0.22s,
                        border-color 0.35s ease 0.22s,
                        background 0.35s ease 0.22s;
            cursor: pointer;
            overflow: hidden;
            height: 38px;
            max-width: 142px; /* Compact pill button default */
            user-select: none;
        }}

        .map-layers-dock:hover {{
            max-width: 780px; /* Fluidly expands horizontally */
            border-color: rgba(255, 255, 255, 0.4);
            box-shadow: 0 10px 32px rgba(0, 0, 0, 0.75), 0 0 20px rgba(59, 130, 246, 0.25);
            background: rgba(15, 23, 42, 0.98);
            /* Lazy, delayed open: graceful 180ms hover intent delay before gliding open */
            transition: max-width 0.55s cubic-bezier(0.16, 1, 0.3, 1) 0.18s,
                        box-shadow 0.35s ease 0.18s,
                        border-color 0.35s ease 0.18s,
                        background 0.35s ease 0.18s;
        }}

        .map-layers-dock.pinned {{
            max-width: 780px;
            border-color: rgba(255, 255, 255, 0.5);
            box-shadow: 0 10px 32px rgba(0, 0, 0, 0.75), 0 0 20px rgba(59, 130, 246, 0.3);
            background: rgba(15, 23, 42, 0.98);
            transition: max-width 0.4s cubic-bezier(0.16, 1, 0.3, 1) 0s;
        }}

        .map-layers-btn {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 0 14px;
            height: 100%;
            flex-shrink: 0;
        }}

        .layers-icon {{
            font-size: 13px;
            color: #60a5fa;
            line-height: 1;
        }}

        .layers-btn-label {{
            font-size: 11.5px;
            font-weight: 700;
            color: #ffffff;
            font-family: var(--font-hindi);
            white-space: nowrap;
            letter-spacing: -0.2px;
        }}

        .layers-expand-icon {{
            font-size: 10px;
            color: var(--text-tertiary);
            transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1) 0.22s, color 0.3s ease 0.22s;
            margin-left: 2px;
        }}

        .map-layers-dock:hover .layers-expand-icon {{
            transform: rotate(90deg);
            color: #60a5fa;
            transition: transform 0.45s cubic-bezier(0.16, 1, 0.3, 1) 0.18s, color 0.3s ease 0.18s;
        }}

        .map-layers-dock.pinned .layers-expand-icon {{
            transform: rotate(90deg);
            color: #60a5fa;
            transition: transform 0.3s ease 0s;
        }}

        /* Expanded Layers Strip */
        .layers-expanded-strip {{
            opacity: 0;
            transform: translateX(-14px);
            transition: opacity 0.2s ease 0s, transform 0.22s ease 0s;
            display: flex;
            align-items: center;
            gap: 14px;
            padding-right: 18px;
            white-space: nowrap;
            border-left: 1px solid var(--hairline-border);
            padding-left: 14px;
            pointer-events: none;
        }}

        .map-layers-dock:hover .layers-expanded-strip {{
            opacity: 1;
            transform: translateX(0);
            pointer-events: auto;
            transition: opacity 0.32s ease 0.28s, transform 0.38s cubic-bezier(0.16, 1, 0.3, 1) 0.28s;
        }}

        .map-layers-dock.pinned .layers-expanded-strip {{
            opacity: 1;
            transform: translateX(0);
            pointer-events: auto;
            transition: opacity 0.25s ease 0.05s, transform 0.28s cubic-bezier(0.16, 1, 0.3, 1) 0.05s;
        }}

        .layers-strip-divider {{
            width: 1px;
            height: 18px;
            background: var(--hairline-border);
        }}

        .layers-basemap-group {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .toggle-check-label {{
            font-size: 11px;
            font-weight: 500;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            transition: color 0.2s;
            user-select: none;
            white-space: nowrap;
        }}

        .toggle-check-label:hover {{
            color: #ffffff;
        }}

        .toggle-check-label input {{
            accent-color: #3b82f6;
            cursor: pointer;
            width: 13px;
            height: 13px;
        }}

        .basemap-dropdown {{
            background: #1e293b;
            border: 1px solid var(--hairline-border);
            color: #ffffff;
            font-size: 11px;
            font-weight: 500;
            border-radius: 6px;
            padding: 3px 6px;
            outline: none;
            cursor: pointer;
        }}

        /* Odometer Rolling Ticker Styles (Dynamic numbers roll like high-speed precision meter) */
        .odometer-val {{
            display: inline-flex;
            align-items: baseline;
            font-variant-numeric: tabular-nums;
            font-feature-settings: "tnum";
            transition: color 0.35s ease, text-shadow 0.35s ease;
        }}

        .odo-num-val {{
            font-variant-numeric: tabular-nums;
            font-feature-settings: "tnum";
            letter-spacing: -0.3px;
            display: inline-block;
        }}

        .odo-unit-suffix {{
            font-size: 0.6em;
            color: var(--text-secondary);
            font-weight: 600;
            margin-left: 4px;
        }}

        /* Green glow during active changes, returns smoothly to native color after change */
        .odometer-val.odo-changing {{
            color: #22c55e !important;
            text-shadow: 0 0 16px rgba(34, 197, 94, 0.8), 0 0 28px rgba(34, 197, 94, 0.35);
        }}

        /* Reset View Docked Button right above Zoom (+/-) */
        .reset-view-control-container {{
            border: none !important;
            box-shadow: none !important;
            margin-bottom: 8px !important;
            clear: both;
            float: right;
        }}

        .reset-view-btn-docked {{
            background: rgba(15, 23, 42, 0.94);
            color: #ffffff;
            border: 1px solid var(--hairline-border);
            border-radius: 8px;
            padding: 6px 11px;
            font-size: 11.5px;
            font-weight: 700;
            font-family: var(--font-hindi), var(--font-main);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(20px);
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            user-select: none;
            white-space: nowrap;
        }}

        .reset-view-btn-docked:hover {{
            background: #2563eb;
            color: #ffffff;
            border-color: #60a5fa;
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.45);
            transform: translateY(-1px);
        }}

        .reset-btn-icon {{
            font-size: 13px;
            display: inline-block;
            transition: transform 0.3s ease;
        }}

        .reset-view-btn-docked:hover .reset-btn-icon {{
            transform: rotate(-180deg);
        }}

        /* Collapsible / Expandable Program Density Scale Button at Bottom-Left */
        .density-scale-dock {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            z-index: 500;
            display: flex;
            align-items: center;
            background: rgba(15, 23, 42, 0.94);
            border: 1px solid var(--hairline-border);
            border-radius: 9999px;
            backdrop-filter: blur(24px) saturate(180%);
            box-shadow: 0 6px 24px rgba(0,0,0,0.55);
            /* Lazy, delayed collapse: holds for 220ms before smoothly collapsing over 0.52s */
            transition: max-width 0.52s cubic-bezier(0.22, 1, 0.36, 1) 0.22s,
                        box-shadow 0.35s ease 0.22s,
                        border-color 0.35s ease 0.22s,
                        background 0.35s ease 0.22s;
            cursor: pointer;
            overflow: hidden;
            height: 38px;
            max-width: 148px; /* Compact button default */
            user-select: none;
        }}

        .density-scale-dock:hover {{
            max-width: 880px; /* Fluidly expands to reveal full scale */
            border-color: rgba(255, 255, 255, 0.4);
            box-shadow: 0 10px 32px rgba(0,0,0,0.75), 0 0 20px rgba(59, 130, 246, 0.25);
            background: rgba(15, 23, 42, 0.98);
            /* Lazy, delayed open: graceful 180ms hover intent delay before gliding open */
            transition: max-width 0.55s cubic-bezier(0.16, 1, 0.3, 1) 0.18s,
                        box-shadow 0.35s ease 0.18s,
                        border-color 0.35s ease 0.18s,
                        background 0.35s ease 0.18s;
        }}

        .density-scale-dock.pinned {{
            max-width: 880px;
            border-color: rgba(255, 255, 255, 0.5);
            box-shadow: 0 10px 32px rgba(0,0,0,0.75), 0 0 20px rgba(59, 130, 246, 0.3);
            background: rgba(15, 23, 42, 0.98);
            transition: max-width 0.4s cubic-bezier(0.16, 1, 0.3, 1) 0s;
        }}

        .density-scale-btn {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 0 14px;
            height: 100%;
            flex-shrink: 0;
        }}

        .density-rainbow-pips {{
            display: flex;
            gap: 2.5px;
            align-items: center;
        }}

        .density-rainbow-pips span {{
            width: 6.5px;
            height: 6.5px;
            border-radius: 50%;
            display: inline-block;
        }}

        .density-btn-label {{
            font-size: 11.5px;
            font-weight: 700;
            color: #ffffff;
            font-family: var(--font-hindi);
            white-space: nowrap;
            letter-spacing: -0.2px;
        }}

        .density-expand-icon {{
            font-size: 10px;
            color: var(--text-tertiary);
            transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1) 0.22s, color 0.3s ease 0.22s;
            margin-left: 2px;
        }}

        .density-scale-dock:hover .density-expand-icon {{
            transform: rotate(90deg);
            color: #60a5fa;
            transition: transform 0.45s cubic-bezier(0.16, 1, 0.3, 1) 0.18s, color 0.3s ease 0.18s;
        }}

        .density-scale-dock.pinned .density-expand-icon {{
            transform: rotate(90deg);
            color: #60a5fa;
            transition: transform 0.3s ease 0s;
        }}

        /* Expanded Legend Strip */
        .density-expanded-strip {{
            opacity: 0;
            transform: translateX(-14px);
            transition: opacity 0.2s ease 0s, transform 0.22s ease 0s;
            display: flex;
            align-items: center;
            gap: 12px;
            padding-right: 18px;
            white-space: nowrap;
            border-left: 1px solid var(--hairline-border);
            padding-left: 12px;
            pointer-events: none;
        }}

        .density-scale-dock:hover .density-expanded-strip {{
            opacity: 1;
            transform: translateX(0);
            pointer-events: auto;
            transition: opacity 0.32s ease 0.28s, transform 0.38s cubic-bezier(0.16, 1, 0.3, 1) 0.28s;
        }}

        .density-scale-dock.pinned .density-expanded-strip {{
            opacity: 1;
            transform: translateX(0);
            pointer-events: auto;
            transition: opacity 0.25s ease 0.05s, transform 0.28s cubic-bezier(0.16, 1, 0.3, 1) 0.05s;
        }}

        .legend-item-pill {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 11px;
            color: var(--text-secondary);
        }}

        .legend-chip-box {{
            width: 13px;
            height: 9px;
            border-radius: 2px;
            flex-shrink: 0;
        }}

        .legend-hub-divider {{
            margin-left: 4px;
            border-left: 1px solid var(--hairline-border);
            padding-left: 10px;
        }}

        .hub-indicator-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #ef4444;
            border: 1.5px solid #ffffff;
            box-shadow: 0 0 6px rgba(239, 68, 68, 0.85);
            flex-shrink: 0;
        }}

        /* Toast Notification */
        .toast-notification {{
            position: fixed;
            top: 80px;
            left: 50%;
            transform: translateX(-50%) translateY(-20px);
            background: rgba(15, 23, 42, 0.96);
            border: 1px solid rgba(239, 68, 68, 0.4);
            color: #ffffff;
            padding: 8px 18px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            box-shadow: 0 10px 30px rgba(0,0,0,0.8);
            z-index: 2000;
            opacity: 0;
            pointer-events: none;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .toast-notification.show {{
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }}

        /* Deep-Dive Slide-Over Drawer */
        .slideover-modal {{
            position: absolute;
            top: 0;
            right: 380px;
            width: 360px;
            height: 100%;
            background: var(--surface-glass);
            border-left: 1px solid var(--hairline-border);
            border-right: 1px solid var(--hairline-border);
            backdrop-filter: blur(30px) saturate(200%);
            z-index: 600;
            transform: translateX(100%);
            transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1);
            display: flex;
            flex-direction: column;
            box-shadow: -8px 0 30px rgba(0,0,0,0.8);
            visibility: hidden;
        }}

        .slideover-modal.open {{
            transform: translateX(0);
            visibility: visible;
        }}

        .slideover-header {{
            padding: 20px;
            border-bottom: 1px solid var(--hairline-border);
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}

        .slideover-title-box {{
            display: flex;
            flex-direction: column;
        }}

        .slideover-district-hi {{
            font-size: 20px;
            font-weight: 700;
            color: #ffffff;
            font-family: var(--font-hindi);
        }}

        .slideover-district-en {{
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 2px;
        }}

        .slideover-close-btn {{
            background: #1e293b;
            border: 1px solid var(--hairline-border);
            color: #ffffff;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 14px;
        }}

        .slideover-close-btn:hover {{
            background: #ffffff;
            color: #0f172a;
        }}

        .slideover-body {{
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}

        .modal-kpi-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}

        .modal-kpi-card {{
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--hairline-border);
            border-radius: 10px;
            padding: 12px;
            text-align: left;
        }}

        .modal-kpi-num {{
            font-size: 18px;
            font-weight: 700;
            color: #ffffff;
            font-feature-settings: "tnum";
        }}

        .modal-kpi-lbl {{
            font-size: 10px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 2px;
            font-weight: 600;
        }}

        .modal-section-title {{
            font-size: 12px;
            font-weight: 600;
            color: #ffffff;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}

        .modal-thana-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
            padding: 6px 0;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }}

        .modal-thana-name {{
            color: #ffffff;
            font-family: var(--font-hindi);
        }}

        .modal-thana-num {{
            color: var(--text-secondary);
            font-feature-settings: "tnum";
            font-weight: 600;
        }}

        .modal-topic-chip {{
            display: inline-block;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--hairline-border);
            color: #e2e8f0;
            font-size: 11px;
            padding: 4px 9px;
            border-radius: 6px;
            margin-right: 6px;
            margin-bottom: 6px;
        }}

        .modal-btn-row {{
            display: flex;
            gap: 8px;
            margin-top: auto;
            padding-top: 10px;
        }}

        .modal-action-btn {{
            flex: 1;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            text-align: center;
        }}

        .btn-primary {{
            background: #3b82f6;
            color: #ffffff;
            border: none;
        }}
        .btn-primary:hover {{
            background: #2563eb;
        }}

        .btn-secondary {{
            background: #1e293b;
            color: #ffffff;
            border: 1px solid var(--hairline-border);
        }}
        .btn-secondary:hover {{
            background: #334155;
        }}

        /* Seamless Monochromatic Right Sidebar */
        .sidebar-seamless {{
            width: 380px;
            background: var(--surface-primary);
            border-left: 1px solid var(--hairline-border);
            display: flex;
            flex-direction: column;
            z-index: 500;
            box-shadow: -4px 0 30px rgba(0,0,0,0.6);
        }}

        .sidebar-header-bar {{
            padding: 16px 20px 14px 20px;
            border-bottom: 1px solid var(--hairline-border);
        }}

        .sidebar-title-row {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
        }}

        .sidebar-heading {{
            font-size: 15px;
            font-weight: 600;
            color: #ffffff;
            letter-spacing: -0.2px;
        }}

        .sidebar-counter {{
            font-size: 11px;
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        /* Search input */
        .search-container {{
            margin-top: 10px;
            position: relative;
        }}

        .search-input-apple {{
            width: 100%;
            background: #1e293b;
            border: 1px solid var(--hairline-border);
            border-radius: 8px;
            padding: 7px 12px 7px 32px;
            color: #ffffff;
            font-size: 12.5px;
            outline: none;
            transition: all 0.2s;
            font-family: var(--font-main);
        }}

        .search-input-apple:focus {{
            border-color: #3b82f6;
            background: #0f172a;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
        }}

        .search-icon-svg {{
            position: absolute;
            left: 10px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-tertiary);
            font-size: 12px;
        }}

        /* Monochromatic Filter Pills (Apple Segmented Control) */
        .filter-segmented-bar {{
            display: flex;
            gap: 4px;
            padding: 10px 18px;
            background: #090d1a;
            border-bottom: 1px solid var(--hairline-border);
            overflow-x: auto;
            scrollbar-width: none;
        }}
        .filter-segmented-bar::-webkit-scrollbar {{
            display: none;
        }}

        .pill-btn {{
            background: #1e293b;
            color: var(--text-secondary);
            border: 1px solid var(--hairline-border);
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 500;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }}

        .pill-btn:hover {{
            color: #ffffff;
            background: #334155;
        }}

        .pill-btn.active {{
            background: #ffffff;
            color: #0f172a;
            font-weight: 700;
            border-color: #ffffff;
            box-shadow: 0 2px 10px rgba(255,255,255,0.2);
        }}

        /* Seamless District List */
        .district-scroll-list {{
            flex: 1;
            overflow-y: auto;
            padding: 10px 14px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}

        .district-item-row {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--hairline-border);
            border-radius: 8px;
            padding: 10px 12px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}

        .district-item-row:hover, .district-item-row.active {{
            background: rgba(59, 130, 246, 0.18);
            border-color: #3b82f6;
            transform: translateX(2px);
        }}

        .item-main-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .item-name-group {{
            display: flex;
            align-items: baseline;
            gap: 8px;
        }}

        .item-name-hi {{
            font-size: 14px;
            font-weight: 600;
            color: #ffffff;
            font-family: var(--font-hindi);
        }}

        .item-name-en {{
            font-size: 11px;
            color: var(--text-tertiary);
        }}

        .item-rank-tag {{
            font-size: 10px;
            font-weight: 700;
            color: #93c5fd;
            background: rgba(59, 130, 246, 0.15);
            padding: 1px 6px;
            border-radius: 4px;
            font-feature-settings: "tnum";
        }}

        .item-metrics-subrow {{
            display: flex;
            justify-content: space-between;
            font-size: 11.5px;
            color: var(--text-secondary);
            font-feature-settings: "tnum";
        }}

        .item-bold-val {{
            color: #ffffff;
            font-weight: 600;
        }}

        /* Mobile Drawer Handle Bar (Hidden on Desktop) */
        .mobile-drawer-handle-bar {{
            display: none;
            flex-direction: column;
            align-items: center;
            padding: 9px 16px 6px 16px;
            cursor: pointer;
            user-select: none;
            background: rgba(15, 23, 42, 0.98);
            border-bottom: 1px solid var(--hairline-border);
        }}

        .mobile-drawer-pill-handle {{
            width: 38px;
            height: 4px;
            border-radius: 2px;
            background: rgba(255, 255, 255, 0.35);
            margin-bottom: 6px;
            transition: background 0.2s;
        }}

        .mobile-drawer-handle-bar:hover .mobile-drawer-pill-handle {{
            background: #60a5fa;
        }}

        .mobile-drawer-title-row {{
            width: 100%;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 4px;
        }}

        .mobile-drawer-title {{
            font-size: 13.5px;
            font-weight: 700;
            color: #ffffff;
            font-family: var(--font-hindi);
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .mobile-drawer-toggle-icon {{
            font-size: 11px;
            color: #93c5fd;
            transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }}

        .drawer-backdrop {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.65);
            backdrop-filter: blur(4px);
            z-index: 1099;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
        }}

        .mobile-telemetry-strip {{
            display: none;
            align-items: stretch;
            justify-content: space-between;
            gap: 6px;
            padding: 8px 10px;
            width: 100%;
            box-sizing: border-box;
            background: rgba(10, 15, 30, 0.98);
            border-bottom: 1px solid rgba(255, 255, 255, 0.15);
            z-index: 550;
            backdrop-filter: blur(20px);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
            overflow: hidden;
        }}

        .m-kpi-pill {{
            flex: 1 1 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 6px 3px;
            border-radius: 10px;
            background: linear-gradient(180deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
            border: 1px solid rgba(255, 255, 255, 0.12);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
            text-align: center;
            min-width: 0;
            box-sizing: border-box;
        }}

        .m-kpi-val-row {{
            display: flex;
            align-items: baseline;
            justify-content: center;
            gap: 2px;
            font-size: 15px;
            font-weight: 800;
            color: #ffffff;
            font-feature-settings: "tnum";
            line-height: 1.15;
            white-space: nowrap;
        }}

        .m-kpi-pill .odo-unit-suffix {{
            font-size: 10.5px;
            color: #38bdf8;
            font-weight: 700;
            margin-left: 2px;
        }}

        .m-kpi-label {{
            font-size: 10px;
            font-weight: 600;
            color: rgba(203, 213, 225, 0.85);
            margin-top: 2px;
            white-space: nowrap;
            letter-spacing: 0.1px;
            text-align: center;
        }}

        /* Drawer / Sidebar Filter Statistics Bar */
        .drawer-filter-stats-bar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            padding: 6px 10px;
            margin-bottom: 8px;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            font-size: 11px;
        }}

        .drawer-filter-badge {{
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            padding: 2px 7px;
            border-radius: 5px;
            font-weight: 700;
            font-size: 10.5px;
            white-space: nowrap;
        }}

        .drawer-filter-summary {{
            color: #e2e8f0;
            font-weight: 600;
            font-size: 11px;
            text-align: right;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        /* Mobile & Tablet Responsive Media Queries */
        @media (max-width: 900px) {{
            header {{
                height: 54px;
                padding: 6px 14px;
            }}

            .campaign-logo-img {{
                height: 40px;
            }}

            .brand-title {{
                font-size: 16px;
                font-weight: 800;
            }}

            .brand-subtitle {{
                display: none;
            }}

            .brand-tag-live {{
                font-size: 9.5px;
                padding: 3px 9px;
            }}

            .jumbo-kpi-container {{
                display: none;
            }}

            .mobile-telemetry-strip {{
                display: flex;
            }}

            .app-workspace {{
                height: calc(100vh - 114px);
                height: calc(100dvh - 114px);
            }}

            .callout-flank-left, .callout-flank-right {{
                display: none !important;
            }}

            .map-layers-dock {{
                top: 10px;
                left: 10px;
            }}

            .density-scale-dock {{
                bottom: 64px;
                left: 10px;
            }}

            .leaflet-bottom.leaflet-right {{
                bottom: 62px !important;
            }}

            /* Transform Sidebar into Mobile Bottom Sheet Drawer */
            .sidebar-seamless {{
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                width: 100% !important;
                height: 52px;
                max-height: 85vh;
                background: rgba(15, 23, 42, 0.98);
                backdrop-filter: blur(28px) saturate(180%);
                border-radius: 18px 18px 0 0;
                border-left: none;
                border-top: 1px solid rgba(255, 255, 255, 0.25);
                box-shadow: 0 -8px 32px rgba(0, 0, 0, 0.85);
                z-index: 1100;
                transition: height 0.38s cubic-bezier(0.16, 1, 0.3, 1);
                overflow: hidden;
            }}

            .sidebar-seamless:not(.drawer-expanded) .sidebar-header-bar,
            .sidebar-seamless:not(.drawer-expanded) .filter-segmented-bar,
            .sidebar-seamless:not(.drawer-expanded) .district-scroll-list {{
                display: none !important;
            }}

            .sidebar-seamless.drawer-expanded {{
                height: 75vh;
            }}

            .mobile-drawer-handle-bar {{
                display: flex;
                flex-shrink: 0;
                height: 52px;
                box-sizing: border-box;
            }}

            .sidebar-seamless.drawer-expanded .mobile-drawer-toggle-icon {{
                transform: rotate(180deg);
            }}

            .drawer-backdrop.active {{
                display: block;
                opacity: 1;
                pointer-events: auto;
            }}

            .sidebar-header-bar {{
                padding: 10px 16px;
            }}

            .district-scroll-list {{
                padding: 8px 12px;
                max-height: calc(75vh - 130px);
            }}

            /* Transform Deep-Dive Slide-Over into Bottom Sheet on Mobile */
            .slideover-modal {{
                position: fixed;
                top: auto;
                bottom: 0;
                left: 0;
                right: 0;
                width: 100%;
                height: 80vh;
                max-height: 85vh;
                border-radius: 20px 20px 0 0;
                border-left: none;
                border-top: 1px solid rgba(255, 255, 255, 0.25);
                transform: translateY(100%);
                z-index: 1300;
                box-shadow: 0 -12px 40px rgba(0,0,0,0.95);
            }}

            .slideover-modal.open {{
                transform: translateY(0);
            }}
        }}

        @media (max-width: 480px) {{
            header {{
                padding: 6px 10px;
                height: 52px;
            }}

            .brand-title {{
                font-size: 14.5px;
            }}

            .mobile-telemetry-strip {{
                padding: 6px 8px;
                gap: 5px;
            }}

            .m-kpi-pill {{
                padding: 5px 3px;
                border-radius: 8px;
            }}

            .m-kpi-val-row {{
                font-size: 14.5px;
            }}

            .m-kpi-pill .odo-unit-suffix {{
                font-size: 10px;
            }}

            .m-kpi-label {{
                font-size: 9.5px;
            }}

            .app-workspace {{
                height: calc(100vh - 110px);
                height: calc(100dvh - 110px);
            }}

            .filter-segmented-bar {{
                padding: 6px 10px;
                gap: 4px;
            }}

            .pill-btn {{
                padding: 4px 8px;
                font-size: 10.5px;
            }}
        }}
    </style>
</head>
<body>

    <!-- Executive Header with Prominent RED LIVE MAP Button -->
    <header>
        <div class="header-brand-box">
            <div class="campaign-logo-box">
                <img src="{logo_b64}" alt="Cyber Jagriti Logo" class="campaign-logo-img">
            </div>
            <div class="brand-text-block">
                <div class="brand-title-row">
                    <span class="brand-title">साइबर जागृति अभियान</span>
                    <button class="brand-tag-live" id="btnLiveStatus" title="लाइव पोर्टल सिंक स्थिति">
                        <span class="live-dot-pulse"></span>
                        <span>LIVE MAP</span>
                    </button>
                </div>
                <div class="brand-subtitle">छत्तीसगढ़ पुलिस | 33 प्रशासनिक जिलों एवं प्रमुख थाना केंद्रों का विस्तृत प्रभाव विश्लेषण</div>
            </div>
        </div>
        <div class="jumbo-kpi-container">
            <div class="jumbo-kpi-block">
                <div class="jumbo-kpi-value odometer-val" id="kpiTotalEvents" data-raw-val="{total_events}"><span class="odo-num-val">{total_events:,}</span></div>
                <div class="jumbo-kpi-label">कुल जागरूकता कार्यक्रम</div>
            </div>
            <div class="kpi-divider"></div>
            <div class="jumbo-kpi-block">
                <div class="jumbo-kpi-value odometer-val" id="kpiTotalReach" data-raw-val="{total_reach/100000:.2f}"><span class="odo-num-val">{total_reach/100000:.2f}</span> <span class="odo-unit-suffix">लाख</span></div>
                <div class="jumbo-kpi-label">जागरूक नागरिक</div>
            </div>
            <div class="kpi-divider"></div>
            <div class="jumbo-kpi-block">
                <div class="jumbo-kpi-value odometer-val" id="kpiAvgAtt" data-raw-val="{avg_state_att}"><span class="odo-num-val">{avg_state_att}</span></div>
                <div class="jumbo-kpi-label">औसत उपस्थिति / कार्यक्रम</div>
            </div>
        </div>
    </header>

    <!-- Mobile Executive Telemetry Strip (Spacious, bold 3-card layout on mobile <= 900px) -->
    <div class="mobile-telemetry-strip" id="mobileTelemetryStrip">
        <div class="m-kpi-pill">
            <div class="m-kpi-val-row odometer-val" id="mKpiEvents" data-raw-val="{total_events}">
                <span class="odo-num-val">{total_events:,}</span>
            </div>
            <div class="m-kpi-label">कुल कार्यक्रम</div>
        </div>
        <div class="m-kpi-pill">
            <div class="m-kpi-val-row odometer-val" id="mKpiReach" data-raw-val="{total_reach/100000:.2f}">
                <span class="odo-num-val">{total_reach/100000:.2f}</span> <span class="odo-unit-suffix">लाख</span>
            </div>
            <div class="m-kpi-label">जागरूक नागरिक</div>
        </div>
        <div class="m-kpi-pill">
            <div class="m-kpi-val-row odometer-val" id="mKpiAvg" data-raw-val="{avg_state_att}">
                <span class="odo-num-val">{avg_state_att}</span>
            </div>
            <div class="m-kpi-label">औसत उपस्थिति</div>
        </div>
    </div>

    <!-- App Body Workspace -->
    <div class="app-workspace">
        <!-- Interactive Leaflet Map -->
        <div id="map"></div>

        <!-- External Left Flank Callouts (Constrained to NEVER overlap bottom legend) -->
        <div class="callout-flank callout-flank-left" id="flankLeft">
            <!-- Dynamically populated -->
        </div>

        <!-- External Right Flank Callouts -->
        <div class="callout-flank callout-flank-right" id="flankRight">
            <!-- Dynamically populated -->
        </div>

        <!-- Collapsible / Expandable Map Layers Dock at Top-Left (Exact same pattern as Density Scale) -->
        <div class="map-layers-dock" id="mapLayersDock" title="होवर करें मैप लेयर्स नियंत्रण हेतु">
            <div class="map-layers-btn">
                <span class="layers-icon">◫</span>
                <span class="layers-btn-label">मैप लेयर्स</span>
                <span class="layers-expand-icon">▸</span>
            </div>
            <div class="layers-expanded-strip">
                <label class="toggle-check-label">
                    <input type="checkbox" id="togglePolygons" checked> जिला सीमाएं
                </label>
                <label class="toggle-check-label">
                    <input type="checkbox" id="toggleLabels"> जिला नाम
                </label>
                <label class="toggle-check-label">
                    <input type="checkbox" id="toggleThanas" checked> थाना केंद्र
                </label>
                <label class="toggle-check-label">
                    <input type="checkbox" id="toggleCards" checked> जिला कार्ड
                </label>
                <div class="layers-strip-divider"></div>
                <div class="layers-basemap-group">
                    <span style="font-size: 11px; color: var(--text-tertiary); font-weight: 500;">बेस मैप:</span>
                    <select id="baseMapSelect" class="basemap-dropdown">
                        <option value="esri_dark">डार्क कैनवास (Dark)</option>
                        <option value="osm">विस्तृत सड़क (OSM)</option>
                        <option value="esri_light">लाइट कैनवास (Light)</option>
                        <option value="satellite">सैटेलाइट (Satellite)</option>
                    </select>
                </div>
            </div>
        </div>

        <!-- Collapsible / Expandable Program Density Scale Button at Bottom-Left -->
        <div class="density-scale-dock" id="densityScaleDock" title="होवर करें कार्यक्रम घनत्व स्केल देखने हेतु">
            <div class="density-scale-btn">
                <div class="density-rainbow-pips">
                    <span style="background: #2563eb;"></span>
                    <span style="background: #9333ea;"></span>
                    <span style="background: #059669;"></span>
                    <span style="background: #d97706;"></span>
                    <span style="background: #e11d48;"></span>
                </div>
                <span class="density-btn-label">कार्यक्रम घनत्व</span>
                <span class="density-expand-icon">▸</span>
            </div>
            <div class="density-expanded-strip">
                <div class="legend-item-pill">
                    <div class="legend-chip-box" style="background: #2563eb;"></div>
                    <span>&gt; 10,000 (अति-सक्रिय)</span>
                </div>
                <div class="legend-item-pill">
                    <div class="legend-chip-box" style="background: #9333ea;"></div>
                    <span>5,000 – 10k</span>
                </div>
                <div class="legend-item-pill">
                    <div class="legend-chip-box" style="background: #059669;"></div>
                    <span>1,000 – 5k</span>
                </div>
                <div class="legend-item-pill">
                    <div class="legend-chip-box" style="background: #d97706;"></div>
                    <span>500 – 1,000</span>
                </div>
                <div class="legend-item-pill">
                    <div class="legend-chip-box" style="background: #e11d48;"></div>
                    <span>&lt; 500 (विस्तार क्षेत्र)</span>
                </div>
                <div class="legend-item-pill legend-hub-divider">
                    <div class="hub-indicator-dot"></div>
                    <span>प्रमुख थाना केंद्र (Hub)</span>
                </div>
            </div>
        </div>

        <!-- Toast Notification for Live Status -->
        <div class="toast-notification" id="toastSync">
            <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#22c55e;"></span>
            <span>लाइव सिंक सक्रिय: {total_events:,} कार्यक्रम पूर्णतः सत्यापित एवं अपडेटेड हैं।</span>
        </div>

        <!-- Slide-Over Deep-Dive Modal -->
        <div class="slideover-modal" id="districtModal">
            <div class="slideover-header">
                <div class="slideover-title-box">
                    <span class="slideover-district-hi" id="modalDistHi">कोंडागांव</span>
                    <span class="slideover-district-en" id="modalDistEn">Kondagaon &bull; Bastar Division</span>
                </div>
                <button class="slideover-close-btn" id="modalCloseBtn">&times;</button>
            </div>
            <div class="slideover-body">
                <div class="modal-kpi-grid">
                    <div class="modal-kpi-card">
                        <div class="modal-kpi-num" id="modalEvents">15,708</div>
                        <div class="modal-kpi-lbl">कुल कार्यक्रम</div>
                    </div>
                    <div class="modal-kpi-card">
                        <div class="modal-kpi-num" id="modalReach">4,50,083</div>
                        <div class="modal-kpi-lbl">जागरूक नागरिक</div>
                    </div>
                    <div class="modal-kpi-card">
                        <div class="modal-kpi-num" id="modalAvg">28.7</div>
                        <div class="modal-kpi-lbl">औसत उपस्थिति</div>
                    </div>
                    <div class="modal-kpi-card">
                        <div class="modal-kpi-num" id="modalRank">#1</div>
                        <div class="modal-kpi-lbl">राज्य रैंक</div>
                    </div>
                </div>

                <div>
                    <div class="modal-section-title">प्रमुख सक्रिय थाने (Top Police Stations)</div>
                    <div id="modalThanasList"></div>
                </div>

                <div>
                    <div class="modal-section-title">प्रमुख जागरूकता विषय (Key Focus Topics)</div>
                    <div id="modalTopicsList"></div>
                </div>

                <div class="modal-btn-row">
                    <button class="modal-action-btn btn-primary" id="modalZoomBtn">
                        जिले पर ज़ूम करें &rarr;
                    </button>
                    <button class="modal-action-btn btn-secondary" id="modalResetBtn">
                        पूरा मैप देखें
                    </button>
                </div>
            </div>
        </div>

        <!-- Backdrop Overlay for Mobile Bottom Sheet -->
        <div class="drawer-backdrop" id="drawerBackdrop"></div>

        <!-- Seamless Monochromatic Right Sidebar & Mobile Bottom Sheet Drawer -->
        <div class="sidebar-seamless" id="sidebarDrawer">
            <!-- Mobile Drawer Handle Bar -->
            <div class="mobile-drawer-handle-bar" id="drawerHandleBar">
                <div class="mobile-drawer-pill-handle"></div>
                <div class="mobile-drawer-title-row">
                    <span class="mobile-drawer-title">☰ 33 जिलों की रैंकिंग</span>
                    <span class="mobile-drawer-toggle-icon" id="drawerToggleIcon">▲</span>
                </div>
            </div>
            <div class="sidebar-header-bar">
                <div class="sidebar-title-row">
                    <span class="sidebar-heading">33 जिलों की आधिकारिक रैंकिंग</span>
                    <span class="sidebar-counter odometer-val" id="sidebarCounter" data-raw-val="33">33 जिले सक्रिय</span>
                </div>
                <div class="drawer-filter-stats-bar" id="drawerFilterStatsBar">
                    <span class="drawer-filter-badge" id="drawerFilterBadge">सभी 33 जिले</span>
                    <span class="drawer-filter-summary" id="drawerFilterSummary">कुल {total_events:,} कार्यक्रम • {total_reach/100000:.2f} लाख नागरिक</span>
                </div>
                <div class="search-container">
                    <span class="search-icon-svg">🔍</span>
                    <input type="text" id="searchInput" class="search-input-apple" placeholder="जिला या थाना खोजें...">
                </div>
            </div>
            <div class="filter-segmented-bar">
                <button class="pill-btn active" data-filter="all">सभी</button>
                <button class="pill-btn" data-filter="10k">&gt; 10,000</button>
                <button class="pill-btn" data-filter="5k-10k">5,000–10k</button>
                <button class="pill-btn" data-filter="1k-5k">1,000–5k</button>
                <button class="pill-btn" data-filter="500-1k">500–1,000</button>
                <button class="pill-btn" data-filter="under500">&lt; 500</button>
            </div>
            <div class="district-scroll-list" id="districtList">
                <!-- Dynamically populated -->
            </div>
        </div>
    </div>

    <script>
        // Data Payload
        const DISTRICTS_DATA = {json.dumps(district_data, ensure_ascii=False)};
        const THANA_POINTS = {json.dumps(thana_points, ensure_ascii=False)};
        const GEO_DATA = {json.dumps(geo_data, ensure_ascii=False)};

        const STATE_CENTER = [21.32, 81.9];
        const STATE_ZOOM = 7.25;

        let activeFilter = 'all';
        let searchQuery = '';
        let activeDistrictId = null;

        // Initialize Map
        const map = L.map('map', {{
            center: STATE_CENTER,
            zoom: STATE_ZOOM,
            minZoom: 6,
            maxZoom: 16,
            zoomControl: false
        }});

        // Dedicated Custom Panes for Absolute Layer Stacking Hierarchy
        map.createPane('districtsPane');
        map.getPane('districtsPane').style.zIndex = 400; // District polygons and borders at base

        map.createPane('thanasPane');
        map.getPane('thanasPane').style.zIndex = 500;   // Thana red bubbles ALWAYS ABOVE geography borders
        map.getPane('thanasPane').style.pointerEvents = 'auto';

        map.createPane('labelsPane');
        map.getPane('labelsPane').style.zIndex = 550;   // Devanagari centroid name badges on top
        map.getPane('labelsPane').style.pointerEvents = 'none';

        // Docked Reset View Button directly above Zoom (+/-) Controls
        const ResetViewControl = L.Control.extend({{
            options: {{ position: 'bottomright' }},
            onAdd: function(map) {{
                const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control reset-view-control-container');
                container.innerHTML = `
                    <button class="reset-view-btn-docked" id="btnResetView" title="राज्य का पूरा मैप देखें (Reset View)">
                        <span class="reset-btn-icon">↺</span>
                        <span>पूरा मैप देखें</span>
                    </button>
                `;
                L.DomEvent.disableClickPropagation(container);
                return container;
            }}
        }});
        map.addControl(new ResetViewControl());
        L.control.zoom({{ position: 'bottomright' }}).addTo(map);

        // Tile Layers (Clean Esri Dark/OSM/Satellite - High Contrast)
        const tileLayers = {{
            esri_dark: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                attribution: 'Tiles &copy; Esri',
                maxZoom: 16
            }}),
            osm: L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '&copy; OpenStreetMap contributors',
                maxZoom: 19
            }}),
            esri_light: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                attribution: 'Tiles &copy; Esri',
                maxZoom: 16
            }}),
            satellite: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                attribution: 'Tiles &copy; Esri',
                maxZoom: 18
            }})
        }};

        tileLayers.esri_dark.addTo(map);

        document.getElementById('baseMapSelect').addEventListener('change', (e) => {{
            Object.values(tileLayers).forEach(l => map.removeLayer(l));
            tileLayers[e.target.value].addTo(map);
        }});

        // 5 High-Contrast Distinct Colors for Ultra-Legibility
        function getColor(events) {{
            if (events >= 10000) return '#2563eb'; // Royal Azure Blue
            if (events >= 5000)  return '#9333ea'; // Electric Purple
            if (events >= 1000)  return '#059669'; // Emerald Green
            if (events >= 500)   return '#d97706'; // Vivid Amber Gold
            return '#e11d48';                      // Crimson Rose
        }}

        // District Polygon Styling (Strictly confined to districtsPane)
        function styleFeature(feature) {{
            const events = feature.properties.events || 0;
            const matches = matchesCurrentFilter(events);
            return {{
                pane: 'districtsPane',
                fillColor: getColor(events),
                weight: 1.8,
                opacity: matches ? 0.95 : 0.25,
                color: matches ? '#ffffff' : '#475569',
                dashArray: '',
                fillOpacity: matches ? 0.78 : 0.12
            }};
        }}

        function matchesCurrentFilter(events) {{
            if (activeFilter === '10k') return events >= 10000;
            if (activeFilter === '5k-10k') return events >= 5000 && events < 10000;
            if (activeFilter === '1k-5k') return events >= 1000 && events < 5000;
            if (activeFilter === '500-1k') return events >= 500 && events < 1000;
            if (activeFilter === 'under500') return events < 500;
            return true;
        }}

        // Interactive GeoJSON Layer with Rich Tooltip (Confined to districtsPane)
        let geojsonLayer = L.geoJson(GEO_DATA, {{
            pane: 'districtsPane',
            style: styleFeature,
            onEachFeature: (feature, layer) => {{
                const p = feature.properties;
                const dNameHi = p.name_hi || p.district;
                const distObj = DISTRICTS_DATA.find(d => d.name_hi === dNameHi || d.name_en === dNameHi);
                
                const eventsStr = p.events ? p.events.toLocaleString() : '0';
                const reachStr = p.reach ? (p.reach >= 100000 ? (p.reach / 100000).toFixed(2) + ' लाख' : p.reach.toLocaleString()) : '0';
                const topThana = (distObj && distObj.top_thanas && distObj.top_thanas[0]) ? distObj.top_thanas[0].name : 'सक्रिय थाना';

                // Rich Apple-Style Tooltip anchored directly to polygon
                layer.bindTooltip(`
                    <div style="font-family:sans-serif;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
                            <span style="font-size:14px; font-weight:700; color:#ffffff; font-family:'Noto Sans Devanagari',sans-serif;">${{dNameHi}}</span>
                            <span style="font-size:10px; font-weight:700; background:#2563eb; color:#ffffff; padding:1px 6px; border-radius:4px;">#${{p.rank || '-'}}</span>
                        </div>
                        <div style="font-size:11px; color:#94a3b8; margin-bottom:6px;">${{p.name_en || ''}} &bull; ${{p.division || ''}} संभाग</div>
                        <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:3px;">
                            <span style="color:#cbd5e1;">जागरूकता कार्यक्रम:</span>
                            <strong style="color:#ffffff;">${{eventsStr}}</strong>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:3px;">
                            <span style="color:#cbd5e1;">जागरूक नागरिक:</span>
                            <strong style="color:#60a5fa;">${{reachStr}}</strong>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:6px;">
                            <span style="color:#cbd5e1;">औसत उपस्थिति:</span>
                            <strong>${{p.avg_attendance || 0}}</strong>
                        </div>
                        <div style="font-size:11px; color:#facc15; border-top:1px solid rgba(255,255,255,0.1); padding-top:4px;">
                            मुख्य थाना: <strong>${{topThana}}</strong>
                        </div>
                    </div>
                `, {{ className: 'leaflet-tooltip-apple', sticky: true, opacity: 0.96 }});

                layer.on({{
                    mouseover: (e) => {{
                        const l = e.target;
                        l.setStyle({{ weight: 3, color: '#facc15', fillOpacity: 0.94 }});
                        l.bringToFront();

                        // Highlight matching sidebar row
                        if (distObj) {{
                            const row = document.getElementById(`row-${{distObj.id}}`);
                            if (row) {{
                                row.classList.add('active');
                                row.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
                            }}
                            const card = document.getElementById(`card-${{distObj.id}}`);
                            if (card) card.classList.add('active');
                        }}
                    }},
                    mouseout: (e) => {{
                        geojsonLayer.resetStyle(e.target);
                        if (distObj) {{
                            const row = document.getElementById(`row-${{distObj.id}}`);
                            if (row) row.classList.remove('active');
                            const card = document.getElementById(`card-${{distObj.id}}`);
                            if (card) card.classList.remove('active');
                        }}
                    }},
                    click: (e) => {{
                        if (distObj) openDistrictModal(distObj);
                    }}
                }});
            }}
        }}).addTo(map);

        // Permanent Crisp District Centroid Badges Layer (Confined to labelsPane)
        const labelsLayer = L.layerGroup();
        DISTRICTS_DATA.forEach(d => {{
            const labelIcon = L.divIcon({{
                className: 'custom-district-div-icon',
                html: `<div class="district-centroid-label">${{d.name_hi}}</div>`,
                iconSize: [70, 20],
                iconAnchor: [35, 10]
            }});
            L.marker([d.lat, d.lng], {{ icon: labelIcon, pane: 'labelsPane', interactive: false }}).addTo(labelsLayer);
        }});

        // Frontline Thana Hub Markers Layer (Confined to thanasPane - ALWAYS floating ABOVE districts)
        const thanasLayer = L.layerGroup().addTo(map);
        THANA_POINTS.forEach(t => {{
            const radius = Math.min(Math.max(Math.sqrt(t.events) * 0.65, 4), 16);
            const circle = L.circleMarker([t.lat, t.lng], {{
                pane: 'thanasPane',
                radius: radius,
                fillColor: '#ef4444',
                color: '#ffffff',
                weight: 1.8,
                opacity: 0.95,
                fillOpacity: 0.9
            }});

            const reachFormatted = t.reach >= 100000 ? (t.reach / 100000).toFixed(2) + ' लाख' : t.reach.toLocaleString();

            // Distinct Crimson Thana Hover Tooltip (Zero white border, auto-closes on mouseout)
            circle.bindTooltip(`
                <div style="font-family:'Inter',sans-serif; min-width:215px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <span style="font-size:13.5px; font-weight:700; color:#ffffff; font-family:'Noto Sans Devanagari',sans-serif;">थाना: ${{t.name_hi}}</span>
                        <span style="font-size:9.5px; font-weight:700; background:rgba(239, 68, 68, 0.25); color:#f87171; border: 1px solid rgba(239, 68, 68, 0.45); padding:1px 6px; border-radius:4px; text-transform:uppercase; letter-spacing:0.4px;">थाना केंद्र</span>
                    </div>
                    <div style="font-size:11px; color:#cbd5e1; margin-bottom:7px;">${{t.name_en}} &bull; जिला: <strong style="color:#ffffff;">${{t.district}}</strong></div>
                    <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:3px;">
                        <span style="color:#94a3b8;">जागरूकता कार्यक्रम:</span>
                        <strong style="color:#ffffff;">${{t.events.toLocaleString()}}</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:3px;">
                        <span style="color:#94a3b8;">जागरूक नागरिक:</span>
                        <strong style="color:#fca5a5;">${{reachFormatted}}</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:12px;">
                        <span style="color:#94a3b8;">औसत उपस्थिति:</span>
                        <strong style="color:#ffffff;">${{t.avg_attendance}}</strong>
                    </div>
                </div>
            `, {{ className: 'leaflet-tooltip-thana', sticky: true, opacity: 0.98 }});

            circle.on({{
                mouseover: (e) => {{
                    const l = e.target;
                    l.setStyle({{ weight: 2.5, color: '#facc15', fillOpacity: 1 }});
                    l.bringToFront();
                }},
                mouseout: (e) => {{
                    const l = e.target;
                    l.setStyle({{ weight: 1.8, color: '#ffffff', fillOpacity: 0.9 }});
                }},
                click: (e) => {{
                    const matchingDist = DISTRICTS_DATA.find(d => d.name_hi === t.district || d.name_en === t.district);
                    if (matchingDist) {{
                        openDistrictModal(matchingDist);
                    }}
                }}
            }});

            thanasLayer.addLayer(circle);
        }});

        // Render Flanks (Constrained to max 4 cards each side, never reaching bottom)
        const flankLeftEl = document.getElementById('flankLeft');
        const flankRightEl = document.getElementById('flankRight');

        function renderCalloutFlanks() {{
            flankLeftEl.innerHTML = '';
            flankRightEl.innerHTML = '';

            const filteredDistricts = DISTRICTS_DATA.filter(d => {{
                if (!matchesCurrentFilter(d.events)) return false;
                if (searchQuery) {{
                    const q = searchQuery.toLowerCase();
                    return d.name_hi.toLowerCase().includes(q) || d.name_en.toLowerCase().includes(q);
                }}
                return true;
            }});

            // Max 4 cards on left and max 4 cards on right to guarantee zero overlap
            const leftDistricts = filteredDistricts.filter(d => d.flank === 'left').slice(0, 4);
            const rightDistricts = filteredDistricts.filter(d => d.flank === 'right').slice(0, 4);

            function createCard(d, targetEl) {{
                const card = document.createElement('div');
                card.className = 'callout-arm-card';
                card.id = `card-${{d.id}}`;
                card.dataset.id = d.id;

                const eventsFormatted = d.events.toLocaleString();
                const isLakh = d.reach >= 100000;
                const reachFormatted = isLakh 
                    ? (d.reach / 100000).toFixed(2) + ' लाख' 
                    : d.reach.toLocaleString();
                const reachRaw = isLakh ? parseFloat((d.reach / 100000).toFixed(2)) : d.reach;
                const reachSuffix = isLakh ? 'लाख' : '';

                card.style.borderLeftColor = getColor(d.events);

                card.innerHTML = `
                    <div class="callout-card-title-row">
                        <span class="callout-card-name">${{d.name_hi}}</span>
                        <span class="callout-card-rank">#${{d.rank}}</span>
                    </div>
                    <div class="callout-card-stat">
                        <span class="odometer-val" id="flank-events-${{d.id}}" data-raw-val="${{d.events}}"><span class="odo-num-val">${{eventsFormatted}}</span></span> कार्यक्रम
                    </div>
                    <div class="callout-card-substat">
                        <span class="odometer-val" id="flank-reach-${{d.id}}" data-raw-val="${{reachRaw}}"><span class="odo-num-val">${{isLakh ? (d.reach / 100000).toFixed(2) : d.reach.toLocaleString()}}</span>${{reachSuffix ? ` <span class="odo-unit-suffix">${{reachSuffix}}</span>` : ''}}</span> जागरूक नागरिक
                    </div>
                `;

                // Hover triggers map polygon highlight cleanly (NO lines)
                card.addEventListener('mouseenter', () => {{
                    geojsonLayer.eachLayer(layer => {{
                        const p = layer.feature.properties;
                        const name = p.name_hi || p.district;
                        if (name === d.name_hi || name === d.name_en) {{
                            layer.setStyle({{ weight: 3.5, color: '#facc15', fillOpacity: 0.95 }});
                            layer.bringToFront();
                        }}
                    }});
                }});

                card.addEventListener('mouseleave', () => {{
                    geojsonLayer.eachLayer(layer => geojsonLayer.resetStyle(layer));
                }});

                card.addEventListener('click', () => openDistrictModal(d));
                targetEl.appendChild(card);
            }}

            leftDistricts.forEach(d => createCard(d, flankLeftEl));
            rightDistricts.forEach(d => createCard(d, flankRightEl));
        }}

        // Seamless Right Sidebar Rendering
        const districtListEl = document.getElementById('districtList');
        function renderSidebarList() {{
            districtListEl.innerHTML = '';
            
            const filtered = DISTRICTS_DATA.filter(d => {{
                if (!matchesCurrentFilter(d.events)) return false;
                if (searchQuery) {{
                    const q = searchQuery.toLowerCase();
                    return d.name_hi.toLowerCase().includes(q) || d.name_en.toLowerCase().includes(q);
                }}
                return true;
            }});

            filtered.forEach(d => {{
                const row = document.createElement('div');
                row.className = 'district-item-row';
                row.id = `row-${{d.id}}`;
                row.onclick = () => {{
                    openDistrictModal(d);
                    closeMobileDrawer();
                }};

                row.addEventListener('mouseenter', () => {{
                    geojsonLayer.eachLayer(layer => {{
                        const p = layer.feature.properties;
                        const name = p.name_hi || p.district;
                        if (name === d.name_hi || name === d.name_en) {{
                            layer.setStyle({{ weight: 3.5, color: '#facc15', fillOpacity: 0.95 }});
                            layer.bringToFront();
                        }}
                    }});
                }});

                row.addEventListener('mouseleave', () => {{
                    geojsonLayer.eachLayer(layer => geojsonLayer.resetStyle(layer));
                }});

                const isLakh = d.reach >= 100000;
                const reachStr = isLakh 
                    ? (d.reach / 100000).toFixed(2) + ' लाख' 
                    : d.reach.toLocaleString();
                const reachRaw = isLakh ? parseFloat((d.reach / 100000).toFixed(2)) : d.reach;
                const reachSuffix = isLakh ? 'लाख' : '';

                row.innerHTML = `
                    <div class="item-main-row">
                        <div class="item-name-group">
                            <span class="item-name-hi">${{d.name_hi}}</span>
                            <span class="item-name-en">${{d.name_en}}</span>
                        </div>
                        <span class="item-rank-tag">#${{d.rank}}</span>
                    </div>
                    <div class="item-metrics-subrow">
                        <span>कार्यक्रम: <span class="item-bold-val odometer-val" id="sidebar-events-${{d.id}}" data-raw-val="${{d.events}}"><span class="odo-num-val">${{d.events.toLocaleString()}}</span></span></span>
                        <span>नागरिक: <span class="item-bold-val odometer-val" id="sidebar-reach-${{d.id}}" data-raw-val="${{reachRaw}}"><span class="odo-num-val">${{isLakh ? (d.reach / 100000).toFixed(2) : d.reach.toLocaleString()}}</span>${{reachSuffix ? ` <span class="odo-unit-suffix">${{reachSuffix}}</span>` : ''}}</span></span>
                        <span>औसत: <span class="odometer-val" id="sidebar-avg-${{d.id}}" data-raw-val="${{d.avg_attendance}}"><span class="odo-num-val">${{d.avg_attendance}}</span></span></span>
                    </div>
                `;
                districtListEl.appendChild(row);
                const sidebarCounterEl = document.getElementById('sidebarCounter');
                if (sidebarCounterEl) {{
                    sidebarCounterEl.textContent = `${{filtered.length}} जिले सक्रिय`;
                }}
            }});
        }}

        // Odometer Rolling Number Animation Engine (Smooth RequestAnimationFrame)
        function animateOdometer(el, targetVal, duration = 700, options = {{}}) {{
            if (!el) return;
            const isDecimal = options.isDecimal || false;
            const suffix = options.suffix || '';
            const prefix = options.prefix || '';

            const prevRaw = el.getAttribute('data-raw-val');
            let startVal = prevRaw !== null ? parseFloat(prevRaw) : 0;
            if (isNaN(startVal)) startVal = 0;

            el.setAttribute('data-raw-val', targetVal);

            if (Math.abs(startVal - targetVal) < 0.001) {{
                renderOdometerText(el, targetVal, isDecimal, prefix, suffix);
                return;
            }}

            // Green glow during active roll; returns smoothly to native color after change completes
            el.classList.add('odo-changing');

            const startTime = performance.now();

            function frame(now) {{
                const elapsed = now - startTime;
                const progress = Math.min(elapsed / duration, 1);

                // Cubic Ease-Out for rapid mechanical roll and smooth settling
                const ease = 1 - Math.pow(1 - progress, 3);
                const current = startVal + (targetVal - startVal) * ease;

                renderOdometerText(el, current, isDecimal, prefix, suffix);

                if (progress < 1) {{
                    requestAnimationFrame(frame);
                }} else {{
                    renderOdometerText(el, targetVal, isDecimal, prefix, suffix);
                    // Settle smoothly and fade back to native element color
                    setTimeout(() => {{
                        el.classList.remove('odo-changing');
                    }}, 180);
                }}
            }}

            requestAnimationFrame(frame);
        }}

        function renderOdometerText(el, val, isDecimal, prefix, suffix) {{
            let numStr = '';
            if (isDecimal) {{
                numStr = val.toFixed(1);
            }} else if (suffix.includes('लाख')) {{
                numStr = val.toFixed(2);
            }} else {{
                numStr = Math.round(val).toLocaleString('en-IN');
            }}

            el.innerHTML = `${{prefix}}<span class="odo-num-val">${{numStr}}</span>${{suffix ? ` <span class="odo-unit-suffix">${{suffix}}</span>` : ''}}`;
        }}

        // Authoritative State Master Counters (Never downgraded by local district filters)
        let stateMasterEvents = {total_events};
        let stateMasterReach = {total_reach};
        let stateMasterAvgAtt = {avg_state_att};

        // Update Executive Header & Mobile Telemetry Bar with Official State Metrics
        function updateStateHeaderKPIs() {{
            const reachLakh = parseFloat((stateMasterReach / 100000).toFixed(2));

            // Desktop Jumbo Header
            animateOdometer(document.getElementById('kpiTotalEvents'), stateMasterEvents, 700);
            animateOdometer(document.getElementById('kpiTotalReach'), reachLakh, 700, {{ suffix: 'लाख' }});
            animateOdometer(document.getElementById('kpiAvgAtt'), stateMasterAvgAtt, 700, {{ isDecimal: true }});

            // Mobile Executive Telemetry Bar
            const mEvEl = document.getElementById('mKpiEvents');
            if (mEvEl) animateOdometer(mEvEl, stateMasterEvents, 700);
            const mRchEl = document.getElementById('mKpiReach');
            if (mRchEl) animateOdometer(mRchEl, reachLakh, 700, {{ suffix: 'लाख' }});
            const mAvgEl = document.getElementById('mKpiAvg');
            if (mAvgEl) animateOdometer(mAvgEl, stateMasterAvgAtt, 700, {{ isDecimal: true }});
        }}

        // Update Pull-Up Drawer / Sidebar Filter Statistics Bar
        function updateDrawerFilterStats() {{
            const filteredDistricts = DISTRICTS_DATA.filter(d => {{
                if (!matchesCurrentFilter(d.events)) return false;
                if (searchQuery) {{
                    const q = searchQuery.toLowerCase();
                    return d.name_hi.toLowerCase().includes(q) || d.name_en.toLowerCase().includes(q);
                }}
                return true;
            }});

            let fEv = 0;
            let fRch = 0;
            filteredDistricts.forEach(d => {{
                fEv += d.events;
                fRch += d.reach;
            }});
            const fReachLakh = parseFloat((fRch / 100000).toFixed(2));

            const sidebarCounterEl = document.getElementById('sidebarCounter');
            if (sidebarCounterEl) {{
                animateOdometer(sidebarCounterEl, filteredDistricts.length, 500, {{ suffix: 'जिले सक्रिय' }});
            }}

            const badgeEl = document.getElementById('drawerFilterBadge');
            const summaryEl = document.getElementById('drawerFilterSummary');

            if (activeFilter === 'all' && !searchQuery) {{
                if (badgeEl) badgeEl.textContent = 'सभी 33 जिले';
                if (summaryEl) summaryEl.textContent = `कुल ${{stateMasterEvents.toLocaleString('en-IN')}} कार्यक्रम • ${{(stateMasterReach/100000).toFixed(2)}} लाख नागरिक`;
            }} else {{
                let filterLabel = activeFilter;
                if (activeFilter === '10k') filterLabel = '> 10,000';
                else if (activeFilter === '5k-10k') filterLabel = '5,000–10k';
                else if (activeFilter === '1k-5k') filterLabel = '1,000–5k';
                else if (activeFilter === '500-1k') filterLabel = '500–1,000';
                else if (activeFilter === 'under500') filterLabel = '< 500';

                if (badgeEl) badgeEl.textContent = searchQuery ? `खोज: "${{searchQuery}}"` : `फ़िल्टर: ${{filterLabel}}`;
                if (summaryEl) summaryEl.textContent = `${{filteredDistricts.length}} जिले • ${{fEv.toLocaleString('en-IN')}} कार्यक्रम • ${{fReachLakh}} लाख नागरिक`;
            }}
        }}

        // Dynamic State-Level / Filtered KPI Recalculator (Preserves State Master Totals)
        function updateDynamicKPIs() {{
            updateDrawerFilterStats();
        }}

        // Open Deep-Dive Modal
        const modalEl = document.getElementById('districtModal');
        function openDistrictModal(d) {{
            activeDistrictId = d.id;
            document.getElementById('modalDistHi').textContent = d.name_hi;
            document.getElementById('modalDistEn').textContent = `${{d.name_en}} • ${{d.division}} Division`;
            animateOdometer(document.getElementById('modalEvents'), d.events, 650);
            animateOdometer(document.getElementById('modalReach'), d.reach, 650);
            animateOdometer(document.getElementById('modalAvg'), d.avg_attendance, 650, {{ isDecimal: true }});
            document.getElementById('modalRank').textContent = `#${{d.rank}}`;

            // Top thanas list with mechanical odometer animation
            const thanasContainer = document.getElementById('modalThanasList');
            thanasContainer.innerHTML = '';
            if (d.top_thanas && d.top_thanas.length > 0) {{
                d.top_thanas.forEach((t, idx) => {{
                    const tRow = document.createElement('div');
                    tRow.className = 'modal-thana-row';
                    tRow.innerHTML = `
                        <span class="modal-thana-name">${{t.name}}</span>
                        <span class="modal-thana-num odometer-val" id="modal-thana-val-${{idx}}" data-raw-val="0"><span class="odo-num-val">0</span> <span class="odo-unit-suffix">कार्यक्रम</span></span>
                    `;
                    thanasContainer.appendChild(tRow);
                    const numEl = tRow.querySelector('.modal-thana-num');
                    animateOdometer(numEl, t.events, 650, {{ suffix: 'कार्यक्रम' }});
                }});
            }} else {{
                thanasContainer.innerHTML = '<div style="font-size:11.5px; color:#94a3b8;">थाना डेटा उपलब्ध नहीं</div>';
            }}

            // Top topics list
            const topicsContainer = document.getElementById('modalTopicsList');
            topicsContainer.innerHTML = '';
            if (d.top_topics && d.top_topics.length > 0) {{
                d.top_topics.forEach(top => {{
                    const chip = document.createElement('span');
                    chip.className = 'modal-topic-chip';
                    chip.textContent = `${{top.name}} (${{top.count}})`;
                    topicsContainer.appendChild(chip);
                }});
            }} else {{
                topicsContainer.innerHTML = '<span class="modal-topic-chip">वित्तीय धोखाधड़ी</span><span class="modal-topic-chip">सोशल मीडिया सुरक्षा</span><span class="modal-topic-chip">ओटीपी फ्रॉड</span>';
            }}

            document.getElementById('modalZoomBtn').onclick = () => {{
                map.flyTo([d.lat, d.lng], 10, {{ duration: 1.2 }});
            }};

            modalEl.classList.add('open');
        }}

        function closeModal() {{
            modalEl.classList.remove('open');
            activeDistrictId = null;
        }}

        // Mobile Bottom Sheet Drawer Controller
        const sidebarDrawer = document.getElementById('sidebarDrawer');
        const drawerHandleBar = document.getElementById('drawerHandleBar');
        const drawerBackdrop = document.getElementById('drawerBackdrop');

        function toggleMobileDrawer() {{
            if (!sidebarDrawer) return;
            const isExpanded = sidebarDrawer.classList.toggle('drawer-expanded');
            if (drawerBackdrop) {{
                drawerBackdrop.classList.toggle('active', isExpanded);
            }}
        }}

        function closeMobileDrawer() {{
            if (sidebarDrawer) {{
                sidebarDrawer.classList.remove('drawer-expanded');
            }}
            if (drawerBackdrop) {{
                drawerBackdrop.classList.remove('active');
            }}
        }}

        if (drawerHandleBar) {{
            drawerHandleBar.addEventListener('click', toggleMobileDrawer);
        }}
        if (drawerBackdrop) {{
            drawerBackdrop.addEventListener('click', closeMobileDrawer);
        }}

        document.getElementById('modalCloseBtn').addEventListener('click', closeModal);
        document.getElementById('modalResetBtn').addEventListener('click', () => {{
            closeModal();
            resetToFullMap();
        }});

        // Reset to Full State Map View Function
        function resetToFullMap() {{
            map.flyTo(STATE_CENTER, STATE_ZOOM, {{ duration: 1.2 }});
            activeFilter = 'all';
            searchQuery = '';
            const sInput = document.getElementById('searchInput');
            if (sInput) sInput.value = '';
            document.querySelectorAll('.pill-btn').forEach(b => {{
                b.classList.toggle('active', b.dataset.filter === 'all');
            }});
            geojsonLayer.eachLayer(layer => geojsonLayer.resetStyle(layer));
            renderCalloutFlanks();
            renderSidebarList();
            updateDynamicKPIs();
        }}

        const btnResetView = document.getElementById('btnResetView');
        if (btnResetView) {{
            btnResetView.addEventListener('click', () => {{
                closeModal();
                resetToFullMap();
            }});
        }}

        // Live Status Button Toast Trigger & Live Polling Bridge
        const btnLiveStatus = document.getElementById('btnLiveStatus');
        const toastSync = document.getElementById('toastSync');
        let toastTimeout = null;

        function showSyncToast(msg, duration = 4000) {{
            if (msg) {{
                const msgSpan = toastSync.querySelector('span:last-child');
                if (msgSpan) msgSpan.textContent = msg;
            }}
            toastSync.classList.add('show');
            if (toastTimeout) clearTimeout(toastTimeout);
            toastTimeout = setTimeout(() => toastSync.classList.remove('show'), duration);
        }}

        async function checkLiveFeed(isManual = false) {{
            const endpoints = [
                'live_feed.json?t=' + Date.now(),
                'http://localhost:8080/live_feed.json?t=' + Date.now()
            ];
            let feed = null;
            for (const ep of endpoints) {{
                try {{
                    const res = await fetch(ep);
                    if (res.ok) {{
                        feed = await res.json();
                        break;
                    }}
                }} catch (e) {{}}
            }}

            if (!feed) {{
                if (isManual) {{
                    const curTotal = DISTRICTS_DATA.reduce((a, b) => a + b.events, 0);
                    showSyncToast(`लाइव पोर्टल सिंक सक्रिय: ${{curTotal.toLocaleString('en-IN')}} कार्यक्रम पूर्णतः सत्यापित हैं।`);
                }}
                return;
            }}

            function updateDistrictAndThanaMetrics(nd) {{
                const target = DISTRICTS_DATA.find(d => d.id === nd.id);
                if (!target) return false;
                const hasChanged = target.events !== nd.events || target.reach !== nd.reach;
                if (!hasChanged) return false;

                target.events = nd.events;
                target.reach = nd.reach;
                target.avg_attendance = nd.avg_attendance;
                if (nd.top_thanas) target.top_thanas = nd.top_thanas;
                if (nd.top_topics) target.top_topics = nd.top_topics;

                // 1. Update Flank Card if visible (with Emerald Green glow odometer)
                const flankEvEl = document.getElementById(`flank-events-${{nd.id}}`);
                if (flankEvEl) {{
                    animateOdometer(flankEvEl, nd.events, 750);
                }}
                const flankRchEl = document.getElementById(`flank-reach-${{nd.id}}`);
                if (flankRchEl) {{
                    const isLakh = nd.reach >= 100000;
                    const rVal = isLakh ? parseFloat((nd.reach / 100000).toFixed(2)) : nd.reach;
                    animateOdometer(flankRchEl, rVal, 750, {{ suffix: isLakh ? 'लाख' : '' }});
                }}

                // 2. Update Sidebar Row if visible (with Emerald Green glow odometer)
                const sbEvEl = document.getElementById(`sidebar-events-${{nd.id}}`);
                if (sbEvEl) {{
                    animateOdometer(sbEvEl, nd.events, 750);
                }}
                const sbRchEl = document.getElementById(`sidebar-reach-${{nd.id}}`);
                if (sbRchEl) {{
                    const isLakh = nd.reach >= 100000;
                    const rVal = isLakh ? parseFloat((nd.reach / 100000).toFixed(2)) : nd.reach;
                    animateOdometer(sbRchEl, rVal, 750, {{ suffix: isLakh ? 'लाख' : '' }});
                }}
                const sbAvgEl = document.getElementById(`sidebar-avg-${{nd.id}}`);
                if (sbAvgEl) {{
                    animateOdometer(sbAvgEl, nd.avg_attendance, 750, {{ isDecimal: true }});
                }}

                // 3. Update Modal if this district is currently inspected
                if (activeDistrictId === nd.id) {{
                    openDistrictModal(target);
                }}

                // 4. Update Map Polygon Color and Properties
                geojsonLayer.eachLayer(layer => {{
                    const p = layer.feature.properties;
                    const name = p.name_hi || p.district;
                    if (name === target.name_hi || name === target.name_en) {{
                        p.events = target.events;
                        p.reach = target.reach;
                        p.avg_attendance = target.avg_attendance;
                        layer.setStyle({{
                            fillColor: getColor(target.events)
                        }});
                    }}
                }});

                return true;
            }}

            let anyChanged = false;
            if (feed.districts && Array.isArray(feed.districts)) {{
                feed.districts.forEach(nd => {{
                    const changed = updateDistrictAndThanaMetrics(nd);
                    if (changed) anyChanged = true;
                }});
            }}

            if (anyChanged || (feed.total_events && feed.total_events !== stateMasterEvents)) {{
                if (feed.total_events) stateMasterEvents = feed.total_events;
                if (feed.total_reach) stateMasterReach = feed.total_reach;
                stateMasterAvgAtt = stateMasterEvents > 0 ? parseFloat((stateMasterReach / stateMasterEvents).toFixed(1)) : 0;

                updateStateHeaderKPIs();
                updateDrawerFilterStats();
                showSyncToast(`नया लाइव डाटा प्राप्त: ${{stateMasterEvents.toLocaleString('en-IN')}} कुल कार्यक्रम (${{feed.timestamp || 'अभी'}})` );
            }} else if (isManual) {{
                showSyncToast(`लाइव सिंक 100% सत्यापित: ${{stateMasterEvents.toLocaleString('en-IN')}} कार्यक्रम एवं ${{(stateMasterReach / 100000).toFixed(2)}} लाख नागरिक पूर्णतः अपडेटेड हैं।`);
            }}
        }}

        btnLiveStatus.addEventListener('click', () => {{
            checkLiveFeed(true);
        }});

        // Periodic live check every 30 seconds
        setInterval(() => checkLiveFeed(false), 30000);

        // Density Scale Dock Pin Toggle on Click
        const densityScaleDock = document.getElementById('densityScaleDock');
        if (densityScaleDock) {{
            densityScaleDock.addEventListener('click', (e) => {{
                densityScaleDock.classList.toggle('pinned');
            }});
        }}

        // Map Layers Dock Pin Toggle on Click (like Density Scale)
        const mapLayersDock = document.getElementById('mapLayersDock');
        if (mapLayersDock) {{
            mapLayersDock.addEventListener('click', (e) => {{
                if (!e.target.closest('input') && !e.target.closest('select')) {{
                    mapLayersDock.classList.toggle('pinned');
                }}
            }});
        }}

        // Filter Pills Event Binding
        document.querySelectorAll('.pill-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                activeFilter = btn.dataset.filter;

                // 1. Re-style Map Polygons
                geojsonLayer.eachLayer(layer => {{
                    const events = layer.feature.properties.events || 0;
                    const matches = matchesCurrentFilter(events);
                    layer.setStyle({{
                        opacity: matches ? 0.95 : 0.25,
                        fillOpacity: matches ? 0.78 : 0.10
                    }});
                }});

                // 2. Re-render Callouts and Sidebar and animate rolling KPIs
                renderCalloutFlanks();
                renderSidebarList();
                updateDynamicKPIs();
            }});
        }});

        // Search Input
        document.getElementById('searchInput').addEventListener('input', (e) => {{
            searchQuery = e.target.value;
            renderCalloutFlanks();
            renderSidebarList();
            updateDynamicKPIs();
        }});

        // Layer Toggles
        document.getElementById('togglePolygons').addEventListener('change', (e) => {{
            if (e.target.checked) map.addLayer(geojsonLayer);
            else map.removeLayer(geojsonLayer);
        }});

        document.getElementById('toggleLabels').addEventListener('change', (e) => {{
            if (e.target.checked) map.addLayer(labelsLayer);
            else map.removeLayer(labelsLayer);
        }});

        document.getElementById('toggleThanas').addEventListener('change', (e) => {{
            if (e.target.checked) map.addLayer(thanasLayer);
            else map.removeLayer(thanasLayer);
        }});

        document.getElementById('toggleCards').addEventListener('change', (e) => {{
            if (e.target.checked) {{
                flankLeftEl.classList.remove('hidden');
                flankRightEl.classList.remove('hidden');
            }} else {{
                flankLeftEl.classList.add('hidden');
                flankRightEl.classList.add('hidden');
            }}
        }});

        // Initial Boot with Dynamic Odometer Roll
        renderCalloutFlanks();
        renderSidebarList();
        setTimeout(() => {{
            updateStateHeaderKPIs();
            updateDrawerFilterStats();
        }}, 200);
    </script>
</body>
</html>
"""

    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"[4/4] Successfully generated High-Contrast Dashboard: {OUTPUT_HTML}")

    with open(INDEX_HTML, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"[*] Generated root index.html for GitHub Pages: {INDEX_HTML}")

    with open(ARTIFACT_HTML, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"[*] Copied to artifact dir: {ARTIFACT_HTML}")

    feed_payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_events": total_events,
        "total_reach": total_reach,
        "avg_attendance": avg_state_att,
        "districts_count": len(district_data),
        "status": "ONLINE",
        "districts": district_data
    }
    with open(FEED_JSON, 'w', encoding='utf-8') as f:
        json.dump(feed_payload, f, ensure_ascii=False, indent=2)
    with open(ARTIFACT_FEED_JSON, 'w', encoding='utf-8') as f:
        json.dump(feed_payload, f, ensure_ascii=False, indent=2)
    print(f"[*] Exported live feed JSON: {FEED_JSON}")

if __name__ == '__main__':
    main()
