import os
import json
import base64
import sqlite3
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "events.db")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")
CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

with open(LOGO_PATH, "rb") as f:
    logo_b64 = base64.b64encode(f.read()).decode("utf-8")

conn = sqlite3.connect(DB_PATH)

# Total stats
cur = conn.cursor()
cur.execute("SELECT COUNT(*), SUM(total_members) FROM events")
tot_events, tot_members = cur.fetchone()

# Dates available
cur.execute("SELECT DISTINCT event_date FROM events WHERE event_date != '' ORDER BY event_date")
dates = [r[0] for r in cur.fetchall()]
latest_date = dates[-1] if dates else "2026-09-05"

cur.execute("SELECT COUNT(*), SUM(total_members) FROM events WHERE event_date = ?", (latest_date,))
today_events, today_members = cur.fetchone()
today_events = today_events or 0
today_members = today_members or 0

# Format date
date_obj = datetime.strptime(latest_date, "%Y-%m-%d")
formatted_date = date_obj.strftime("%d %B %Y")

# Top 5 and Bottom 5 Districts
cur.execute("""
SELECT district_name_en, district_name_hi, COUNT(*) as cnt, SUM(total_members) as mem
FROM events
WHERE district_name_en != ''
GROUP BY district_name_en
ORDER BY cnt DESC
""")
all_districts = cur.fetchall()
top_five = all_districts[:5]
bottom_five = all_districts[-5:]

# Table 1: Attendance Size Buckets
buckets_sql = """
SELECT 
    CASE 
        WHEN total_members < 5 THEN '1. पांच से कम नागरिक (< 5)'
        WHEN total_members BETWEEN 5 AND 10 THEN '2. 5 से 10 नागरिक'
        WHEN total_members BETWEEN 11 AND 25 THEN '3. 11 से 25 नागरिक'
        WHEN total_members BETWEEN 26 AND 50 THEN '4. 26 से 50 नागरिक'
        WHEN total_members BETWEEN 51 AND 100 THEN '5. 51 से 100 नागरिक'
        WHEN total_members BETWEEN 101 AND 200 THEN '6. 101 से 200 नागरिक'
        WHEN total_members BETWEEN 201 AND 300 THEN '7. 201 से 300 नागरिक'
        WHEN total_members BETWEEN 301 AND 500 THEN '8. 301 से 500 नागरिक'
        ELSE '9. 500 से अधिक नागरिक (> 500)'
    END AS bucket_name,
    CASE 
        WHEN total_members < 5 THEN 'सूक्ष्म जनसंपर्क (Micro-Outreach)'
        WHEN total_members BETWEEN 5 AND 10 THEN 'लघु समूह संपर्क (Small Groups)'
        WHEN total_members BETWEEN 11 AND 25 THEN 'कक्षा / टोली सत्र (Classroom/Group)'
        WHEN total_members BETWEEN 26 AND 50 THEN 'सामुदायिक समूह बैठक (Community Session)'
        WHEN total_members BETWEEN 51 AND 100 THEN 'संस्थानिक सत्र (Institutional Session)'
        WHEN total_members BETWEEN 101 AND 200 THEN 'बृहद जनसभा (Large Community Hall)'
        WHEN total_members BETWEEN 201 AND 300 THEN 'कॉलेज / विद्यालय सम्मेलन (Auditorium)'
        WHEN total_members BETWEEN 301 AND 500 THEN 'क्षेत्रीय टाउनहॉल (Regional Town Hall)'
        ELSE 'विशाल जन जागरूकता रैली (Mega Rally)'
    END AS category_desc,
    COUNT(*) AS total_events,
    SUM(total_members) AS total_citizens,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM events), 2) AS pct_events,
    ROUND(SUM(total_members) * 100.0 / (SELECT SUM(total_members) FROM events), 2) AS pct_citizens
FROM events
GROUP BY bucket_name
ORDER BY bucket_name;
"""
cur.execute(buckets_sql)
bucket_rows = cur.fetchall()

# Table 2: District-wise Outreach Profile
dist_profile_sql = """
SELECT 
    district_name_hi,
    district_name_en,
    COUNT(*) AS total_events,
    SUM(CASE WHEN total_members < 10 THEN 1 ELSE 0 END) AS under_10,
    ROUND(SUM(CASE WHEN total_members < 10 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_under_10,
    SUM(CASE WHEN total_members BETWEEN 10 AND 100 THEN 1 ELSE 0 END) AS between_10_100,
    SUM(CASE WHEN total_members > 100 THEN 1 ELSE 0 END) AS over_100,
    ROUND(SUM(CASE WHEN total_members > 100 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_over_100,
    SUM(total_members) AS total_members
FROM events
WHERE district_name_en != ''
GROUP BY district_name_en
ORDER BY total_events DESC
LIMIT 14;
"""
cur.execute(dist_profile_sql)
dist_profile_rows = cur.fetchall()

# Table 3: Top Performing Thanas (cleaned bilingual)
thana_clean_sql = """
SELECT 
    CASE 
        WHEN police_station IN ('Devbhog', 'देवभोग') THEN 'देवभोग (Devbhog)'
        WHEN police_station IN ('Panduka', 'पाण्डुका') THEN 'पाण्डुका (Panduka)'
        WHEN police_station IN ('Fingeshwar', 'फिंगेश्वर') THEN 'फिंगेश्वर (Fingeshwar)'
        WHEN police_station IN ('Vishrampuri', 'विश्रामपुरी') THEN 'विश्रामपुरी (Vishrampuri)'
        WHEN police_station IN ('Keshkal', 'केशकाल') THEN 'केशकाल (Keshkal)'
        WHEN police_station IN ('थाना बड़े डोंगर', 'Badedongar') THEN 'बड़े डोंगर (Badedongar)'
        WHEN police_station IN ('Dongargarh', 'डोंगरगढ़') THEN 'डोंगरगढ़ (Dongargarh)'
        WHEN police_station IN ('Rajim', 'राजिम') THEN 'राजिम (Rajim)'
        WHEN police_station IN ('Police line', 'Police Line Bilaspur', 'Police line bilaspur') THEN 'पुलिस लाइन (Police Line)'
        WHEN police_station IN ('पुरानी भिलाई', 'Old Bhilai') THEN 'पुरानी भिलाई (Old Bhilai)'
        ELSE police_station
    END AS clean_thana,
    district_name_en AS district,
    COUNT(*) AS total_events,
    SUM(total_members) AS total_reach,
    ROUND(AVG(total_members), 1) AS avg_per_event
FROM events
WHERE police_station != ''
GROUP BY clean_thana, district_name_en
ORDER BY total_events DESC
LIMIT 12;
"""
cur.execute(thana_clean_sql)
thana_rows = cur.fetchall()

conn.close()

# Generate HTML
html = f"""<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<title>Cyber Jagriti Abhiyan - Comprehensive Analytics Report</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Noto+Sans+Devanagari:wght@400;500;600;700;800&display=swap');

@page {{
    size: A4 portrait;
    margin: 8mm 12mm 10mm 12mm;
}}

* {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}}

body {{
    background-color: #F7F2E1;
    font-family: 'Plus Jakarta Sans', 'Noto Sans Devanagari', sans-serif;
    color: #2D3748;
    line-height: 1.4;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}}

.report-page {{
    page-break-after: always;
    min-height: 1040px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    margin-bottom: 20px;
}}

.report-page:last-child {{
    page-break-after: auto;
    margin-bottom: 0;
}}

.content-wrap {{
    flex: 1;
}}

/* Header */
.header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
    background: rgba(255, 255, 255, 0.75);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(210, 195, 160, 0.6);
    border-radius: 12px;
    margin-bottom: 12px;
}}

.header-mini {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 14px;
    background: rgba(255, 255, 255, 0.6);
    border: 1px solid rgba(210, 195, 160, 0.5);
    border-radius: 10px;
    margin-bottom: 12px;
}}

.logo-img {{
    width: 60px;
    height: 60px;
    object-fit: contain;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.08));
}}

.logo-img-mini {{
    width: 32px;
    height: 32px;
    object-fit: contain;
}}

.header-text h1 {{
    font-size: 22px;
    font-weight: 800;
    color: #1A365D;
    letter-spacing: -0.3px;
}}

.header-text .subtitle {{
    font-size: 13px;
    font-weight: 600;
    color: #C05621;
    display: flex;
    align-items: center;
    gap: 8px;
}}

.header-text .subtitle span {{
    color: #4A5568;
    font-weight: 500;
}}

.badge-date {{
    background: #1A365D;
    color: #FFF;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 11.5px;
    font-weight: 700;
    text-align: right;
}}

.section-label {{
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #718096;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
}}

.section-label::before {{
    content: '';
    display: inline-block;
    width: 4px;
    height: 12px;
    background: #2B6CB0;
    border-radius: 2px;
}}

/* Stat Cards */
.stats-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
    margin-bottom: 12px;
}}

.stat-card {{
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid rgba(210, 195, 160, 0.6);
    border-radius: 12px;
    padding: 10px 16px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.03);
}}

.stat-card.total-primary {{
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(235, 248, 255, 0.85));
    border-left: 4px solid #2B6CB0;
}}

.stat-card.total-secondary {{
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(254, 235, 226, 0.85));
    border-left: 4px solid #DD6B20;
}}

.stat-card.today-primary {{
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(240, 255, 244, 0.85));
    border-left: 4px solid #38A169;
}}

.stat-card.today-secondary {{
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(250, 245, 255, 0.85));
    border-left: 4px solid #805AD5;
}}

.stat-card .card-title {{
    font-size: 13px;
    font-weight: 700;
    color: #2D3748;
    margin-bottom: 2px;
}}

.stat-card .card-value {{
    font-size: 24px;
    font-weight: 800;
    color: #1A202C;
    letter-spacing: -0.4px;
}}

.stat-card .card-meta {{
    font-size: 10.5px;
    font-weight: 500;
    color: #718096;
}}

/* Card Sections */
.card-section {{
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid rgba(210, 195, 160, 0.6);
    border-radius: 12px;
    padding: 12px 16px;
    margin-bottom: 12px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.03);
}}

.card-heading {{
    font-size: 14px;
    font-weight: 800;
    color: #1A365D;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}}

.card-heading .tag {{
    font-size: 10px;
    font-weight: 700;
    background: #EBF8FF;
    color: #2B6CB0;
    padding: 2px 8px;
    border-radius: 8px;
}}

.analysis-points {{
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 6px;
}}

.analysis-points li {{
    font-size: 11.5px;
    color: #2D3748;
    position: relative;
    padding-left: 18px;
    line-height: 1.45;
}}

.analysis-points li::before {{
    content: "•";
    color: #2B6CB0;
    font-size: 16px;
    position: absolute;
    left: 4px;
    top: -2px;
}}

/* Tables Grid */
.tables-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 12px;
}}

.table-card {{
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid rgba(210, 195, 160, 0.6);
    border-radius: 12px;
    padding: 10px 14px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    margin-bottom: 12px;
}}

.table-title {{
    font-size: 13px;
    font-weight: 800;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}

.table-title.top-title {{ color: #22543D; }}
.table-title.bottom-title {{ color: #742A2A; }}

.table-title .badge {{
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 8px;
    font-weight: 700;
}}

.badge-top {{ background: #C6F6D5; color: #22543D; }}
.badge-bottom {{ background: #FED7D7; color: #742A2A; }}
.badge-info {{ background: #E2E8F0; color: #2D3748; }}

table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
}}

th {{
    text-align: left;
    padding: 5px 6px;
    font-size: 10px;
    font-weight: 700;
    color: #4A5568;
    background: rgba(240, 235, 220, 0.4);
    border-bottom: 1px solid #CBD5E0;
    text-transform: uppercase;
}}

th.text-right, td.text-right {{
    text-align: right;
}}

td {{
    padding: 5px 6px;
    border-bottom: 1px solid rgba(226, 232, 240, 0.6);
    color: #2D3748;
}}

tr:last-child td {{
    border-bottom: none;
}}

tr:hover {{
    background: rgba(255, 255, 255, 0.5);
}}

.rank {{
    display: inline-block;
    width: 18px;
    height: 18px;
    line-height: 18px;
    text-align: center;
    border-radius: 50%;
    font-size: 10px;
    font-weight: 700;
}}

.rank-top {{ background: #EBF8FF; color: #2B6CB0; }}
.rank-bottom {{ background: #FFF5F5; color: #E53E3E; }}

.district-name {{
    font-weight: 700;
    color: #1A202C;
}}

.district-sub {{
    font-size: 9.5px;
    color: #718096;
    font-weight: 500;
}}

/* Action Plan */
.action-card {{
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid rgba(210, 195, 160, 0.6);
    border-radius: 12px;
    padding: 12px 16px;
    border-left: 4px solid #C05621;
    box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    margin-bottom: 12px;
}}

.action-heading {{
    font-size: 14px;
    font-weight: 800;
    color: #7B341E;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}}

.action-list {{
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 6px;
}}

.action-list li {{
    font-size: 11.5px;
    color: #2D3748;
    position: relative;
    padding-left: 18px;
    line-height: 1.45;
}}

.action-list li::before {{
    content: "➔";
    color: #C05621;
    font-size: 11px;
    position: absolute;
    left: 2px;
    top: 1px;
}}

/* Footer */
.footer {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 6px;
    border-top: 1px solid rgba(210, 195, 160, 0.5);
    font-size: 10px;
    color: #718096;
}}
</style>
</head>
<body>

<!-- ======================================================== -->
<!-- PAGE 1: EXECUTIVE DASHBOARD & HIGH-LEVEL TELEMETRY       -->
<!-- ======================================================== -->
<div class="report-page">
    <div class="content-wrap">
        <div class="header">
            <div class="header-left">
                <img class="logo-img" src="data:image/png;base64,{logo_b64}" alt="Cyber Jagriti Logo">
                <div class="header-text">
                    <h1>साइबर जागृति अभियान</h1>
                    <div class="subtitle">दैनिक प्रशासनिक एनालिटिक्स रिपोर्ट <span>(Executive Analytics Report)</span></div>
                </div>
            </div>
            <div class="badge-date">
                तारीख: {formatted_date}<br>
                <span style="font-size: 10px; opacity: 0.85; font-weight: 500;">स्टेट नोडल डैशबोर्ड (9:00 PM Snapshot)</span>
            </div>
        </div>

        <!-- 1. Total Stats -->
        <div class="section-label">1. कुल राज्य आंकड़े (Overall Campaign Stats)</div>
        <div class="stats-grid">
            <div class="stat-card total-primary">
                <div class="card-title">कुल जागरूक नागरिक (Total Aware)</div>
                <div class="card-value">{tot_members:,}</div>
                <div class="card-meta">समस्त 34 जिलों में कुल प्रत्यक्ष जनसंपर्क (Cumulative Outreach)</div>
            </div>
            <div class="stat-card total-secondary">
                <div class="card-title">कुल राज्य प्रविष्टियाँ (Total Events)</div>
                <div class="card-value">{tot_events:,}</div>
                <div class="card-meta">अभियान के तहत कुल आयोजित जागरूकता कार्यक्रम व आधिकारिक एंट्रीज</div>
            </div>
        </div>

        <!-- 2. Today's Stats -->
        <div class="section-label">2. आज की गतिविधि (Today's Operational Stats - {formatted_date})</div>
        <div class="stats-grid">
            <div class="stat-card today-primary">
                <div class="card-title">आज के कुल इवेंट (Today's Events)</div>
                <div class="card-value">{today_events:,}</div>
                <div class="card-meta">पूरे कार्यदिवस (9 AM - 9 PM) में दर्ज नवीन जागरूकता कार्यक्रम</div>
            </div>
            <div class="stat-card today-secondary">
                <div class="card-title">आज जागरूक नागरिक (Today's Aware)</div>
                <div class="card-value">{today_members:,}</div>
                <div class="card-meta">आज के कार्यक्रमों से प्रत्यक्ष रूप से लाभान्वित कुल नागरिक</div>
            </div>
        </div>

        <!-- 3. Executive Analysis -->
        <div class="card-section">
            <div class="card-heading">
                कार्यकारी अवलोकन एवं सामरिक विश्लेषण (Executive Analysis & Strategic Overview)
                <span class="tag">Operational Review</span>
            </div>
            <ul class="analysis-points">
                <li><strong>संचालन तीव्रता (Operational Momentum):</strong> आज कार्यदिवस में कुल <strong>{today_events:,} नवीन कार्यक्रम</strong> पोर्टल पर प्रविष्ट हुए, जिससे single-day reach <strong>{today_members:,} नागरिकों</strong> तक पहुंची। बस्तर एवं मध्य संभाग में कार्यक्रम संचालन की गति सुदृढ़ बनी हुई है।</li>
                <li><strong>सहभागिता घनत्व एवं प्रभावशीलता (Outreach Density):</strong> डेटा विश्लेषण से स्पष्ट है कि राज्य में दो प्रकार के outreach मॉडल सक्रिय हैं: उच्च-आवृत्ति सूक्ष्म संपर्क (Micro-Outreach: &lt;10 नागरिक) तथा व्यापक संस्थानिक जनसभाएं (&gt;100 नागरिक)। बिलासपुर एवं दुर्ग जिलों में प्रति-इवेंट औसत सहभागिता (Average Reach) राज्य औसत से उल्लेखनीय रूप से अधिक है।</li>
                <li><strong>डेटा रिपोर्टिंग एवं समन्वय आवश्यकता:</strong> निचले 5 जिलों (विशेष रूप से रायपुर कमिश्नरेट, नारायणपुर एवं महासमुंद) में दैनिक प्रविष्टि की गति अपेक्षाकृत सीमित है। फील्ड स्तर पर आयोजित गतिविधियों के उपरांत उसी कार्यदिवस में पोर्टल अद्यतनीकरण (Same-day Sync) सुनिश्चित करना आवश्यक है।</li>
            </ul>
        </div>

        <!-- 4. Top 5 and Bottom 5 Districts -->
        <div class="tables-grid">
            <div class="table-card">
                <div class="table-title top-title">
                    <span>शीर्ष 5 जिले (Top 5 Districts)</span>
                    <span class="badge badge-top">उच्च गतिविधि</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th style="width: 28px;">#</th>
                            <th>जिला (District)</th>
                            <th class="text-right">कुल इवेंट</th>
                            <th class="text-right">जागरूक नागरिक</th>
                        </tr>
                    </thead>
                    <tbody>"""

for idx, (en, hi, cnt, mem) in enumerate(top_five, 1):
    html += f"""
                        <tr>
                            <td><span class="rank rank-top">{idx}</span></td>
                            <td><div class="district-name">{hi}</div><div class="district-sub">{en}</div></td>
                            <td class="text-right" style="font-weight: 700; color: #2B6CB0;">{cnt:,}</td>
                            <td class="text-right" style="font-weight: 600;">{mem:,}</td>
                        </tr>"""

html += """
                    </tbody>
                </table>
            </div>

            <div class="table-card">
                <div class="table-title bottom-title">
                    <span>निचले 5 जिले (Bottom 5 Districts)</span>
                    <span class="badge badge-bottom">प्राथमिकता क्षेत्र</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th style="width: 28px;">#</th>
                            <th>जिला (District)</th>
                            <th class="text-right">कुल इवेंट</th>
                            <th class="text-right">जागरूक नागरिक</th>
                        </tr>
                    </thead>
                    <tbody>"""

for idx, (en, hi, cnt, mem) in enumerate(bottom_five, 1):
    html += f"""
                        <tr>
                            <td><span class="rank rank-bottom">{idx}</span></td>
                            <td><div class="district-name">{hi}</div><div class="district-sub">{en.strip()}</div></td>
                            <td class="text-right" style="font-weight: 700; color: #C53030;">{cnt:,}</td>
                            <td class="text-right" style="font-weight: 600;">{mem:,}</td>
                        </tr>"""

html += f"""
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <div class="footer">
        <div>साइबर जागृति अभियान - छत्तीसगढ़ पुलिस (सत्यमेव जयते)</div>
        <div>पृष्ठ 1 / 3 | Confidential & Official Administrative Use Only</div>
    </div>
</div>

<!-- ======================================================== -->
<!-- PAGE 2: DETAILED ATTENDANCE BUCKETS & DISTRICT PROFILES -->
<!-- ======================================================== -->
<div class="report-page">
    <div class="content-wrap">
        <div class="header-mini">
            <div style="display: flex; align-items: center; gap: 8px;">
                <img class="logo-img-mini" src="data:image/png;base64,{logo_b64}" alt="Logo">
                <strong style="color: #1A365D; font-size: 13px;">साइबर जागृति अभियान</strong>
                <span style="color: #718096; font-size: 12px;">| सहभागिता आकार एवं जिला प्रोफाइल विश्लेषण</span>
            </div>
            <div style="font-size: 11px; font-weight: 600; color: #4A5568;">तारीख: {formatted_date}</div>
        </div>

        <!-- Table 1: Attendance Size Distribution -->
        <div class="table-card">
            <div class="table-title" style="color: #1A365D;">
                <span>सहभागिता आकार वितरण (Attendance Cohort & Scale Distribution)</span>
                <span class="badge badge-info">कुल विश्लेषित इवेंट: {tot_events:,}</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 25%;">उपस्थिति सीमा (Audience Cohort)</th>
                        <th style="width: 30%;">कार्यक्रम श्रेणी (Session Category)</th>
                        <th class="text-right" style="width: 15%;">आयोजन संख्या</th>
                        <th class="text-right" style="width: 12%;">इवेंट प्रतिशत</th>
                        <th class="text-right" style="width: 18%;">कुल नागरिक सहभागिता</th>
                    </tr>
                </thead>
                <tbody>"""

for row in bucket_rows:
    b_name, b_cat, b_events, b_cits, b_pct_ev, b_pct_cit = row
    b_name_clean = b_name.split(". ")[1]
    html += f"""
                    <tr>
                        <td style="font-weight: 700; color: #2D3748;">{b_name_clean}</td>
                        <td style="color: #4A5568;">{b_cat}</td>
                        <td class="text-right" style="font-weight: 700; color: #2B6CB0;">{b_events:,}</td>
                        <td class="text-right" style="font-weight: 600;">{b_pct_ev:.1f}%</td>
                        <td class="text-right" style="font-weight: 700; color: #1A202C;">{b_cits:,} <span style="font-size: 9.5px; color: #718096;">({b_pct_cit:.1f}%)</span></td>
                    </tr>"""

html += f"""
                </tbody>
            </table>
            <div style="font-size: 10.5px; color: #4A5568; margin-top: 8px; line-height: 1.45; background: rgba(240, 235, 220, 0.4); padding: 6px 10px; border-radius: 6px;">
                <strong>सामरिक अंतर्दृष्टि (Strategic Insight):</strong> 11 से 50 नागरिकों के छोटे समूह सत्र राज्य के आयोजनों का <strong>54.5%</strong> हिस्सा हैं, जो गहन जागरूकता हेतु अत्यंत प्रभावी हैं। वहीं, 500 से अधिक नागरिकों के 499 विशाल आयोजनों (1.15%) ने राज्य के कुल रीच का लगभग <strong>24.8% जनसमूह</strong> आच्छादित किया है।
            </div>
        </div>

        <!-- Table 2: District-wise Outreach Profile -->
        <div class="table-card">
            <div class="table-title" style="color: #1A365D;">
                <span>जिला-वार कार्यक्रम स्वरूप तुलना (District Outreach Profile: Micro vs Mass Events)</span>
                <span class="badge badge-info">प्रमुख 14 जिले</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>जिला (District)</th>
                        <th class="text-right">कुल इवेंट</th>
                        <th class="text-right">सूक्ष्म सत्र (&lt;10)</th>
                        <th class="text-right">सूक्ष्म %</th>
                        <th class="text-right">मध्यम सत्र (10-100)</th>
                        <th class="text-right">सामूहिक सत्र (&gt;100)</th>
                        <th class="text-right">सामूहिक %</th>
                        <th class="text-right">कुल नागरिक पहुंच</th>
                    </tr>
                </thead>
                <tbody>"""

for r in dist_profile_rows:
    d_hi, d_en, d_tot, d_u10, d_pct_u10, d_10_100, d_o100, d_pct_o100, d_mem = r
    html += f"""
                    <tr>
                        <td><span style="font-weight: 700;">{d_hi}</span> <span style="font-size: 9.5px; color: #718096;">({d_en})</span></td>
                        <td class="text-right" style="font-weight: 700; color: #2B6CB0;">{d_tot:,}</td>
                        <td class="text-right">{d_u10:,}</td>
                        <td class="text-right" style="color: {'#C53030' if d_pct_u10 > 25 else '#4A5568'}; font-weight: 600;">{d_pct_u10:.1f}%</td>
                        <td class="text-right">{d_10_100:,}</td>
                        <td class="text-right" style="font-weight: 700; color: #22543D;">{d_o100:,}</td>
                        <td class="text-right" style="color: {'#22543D' if d_pct_o100 > 15 else '#4A5568'}; font-weight: 600;">{d_pct_o100:.1f}%</td>
                        <td class="text-right" style="font-weight: 700;">{d_mem:,}</td>
                    </tr>"""

html += f"""
                </tbody>
            </table>
            <div style="font-size: 10.5px; color: #4A5568; margin-top: 8px; line-height: 1.45; background: rgba(240, 235, 220, 0.4); padding: 6px 10px; border-radius: 6px;">
                <strong>संरचनात्मक विश्लेषण (Structural Analysis):</strong> बिलासपुर एवं बेमेतरा जिलों ने 20%+ आयोजनों में 100+ नागरिकों की सहभागिता सुनिश्चित कर उच्चतम औसत रीच हासिल की है। कोंडागांव व गरियाबंद ने व्यापक ग्रामीण संपर्क हेतु सूक्ष्म सत्रों का अधिकतम उपयोग किया है।
            </div>
        </div>
    </div>
    <div class="footer">
        <div>साइबर जागृति अभियान - छत्तीसगढ़ पुलिस (सत्यमेव जयते)</div>
        <div>पृष्ठ 2 / 3 | Confidential & Official Administrative Use Only</div>
    </div>
</div>

<!-- ======================================================== -->
<!-- PAGE 3: THANA PERFORMANCE & ADMINISTRATIVE ACTION PLAN    -->
<!-- ======================================================== -->
<div class="report-page">
    <div class="content-wrap">
        <div class="header-mini">
            <div style="display: flex; align-items: center; gap: 8px;">
                <img class="logo-img-mini" src="data:image/png;base64,{logo_b64}" alt="Logo">
                <strong style="color: #1A365D; font-size: 13px;">साइबर जागृति अभियान</strong>
                <span style="color: #718096; font-size: 12px;">| थाना-स्तरीय प्रदर्शन एवं आगे की कार्यवाही</span>
            </div>
            <div style="font-size: 11px; font-weight: 600; color: #4A5568;">तारीख: {formatted_date}</div>
        </div>

        <!-- Table 3: Top Performing Thanas -->
        <div class="table-card">
            <div class="table-title" style="color: #1A365D;">
                <span>शीर्ष सक्रिय पुलिस थाने (Key Performing Police Stations / Units)</span>
                <span class="badge badge-top">राज्य स्तरीय अग्रणी थाने</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 32px;">#</th>
                        <th>थाना / पुलिस इकाई (Police Station)</th>
                        <th>जिला (District)</th>
                        <th class="text-right">कुल आयोजित इवेंट</th>
                        <th class="text-right">कुल जागरूक नागरिक</th>
                        <th class="text-right">प्रति-इवेंट औसत सहभागिता</th>
                    </tr>
                </thead>
                <tbody>"""

for idx, t in enumerate(thana_rows, 1):
    t_name, t_dist, t_cnt, t_reach, t_avg = t
    html += f"""
                    <tr>
                        <td><span class="rank rank-top">{idx}</span></td>
                        <td style="font-weight: 700; color: #1A202C;">{t_name}</td>
                        <td style="color: #4A5568; font-weight: 500;">{t_dist}</td>
                        <td class="text-right" style="font-weight: 700; color: #2B6CB0;">{t_cnt:,}</td>
                        <td class="text-right" style="font-weight: 700;">{t_reach:,}</td>
                        <td class="text-right" style="font-weight: 600; color: {'#22543D' if t_avg > 40 else '#4A5568'};">{t_avg}</td>
                    </tr>"""

html += f"""
                </tbody>
            </table>
            <div style="font-size: 10.5px; color: #4A5568; margin-top: 8px; line-height: 1.45; background: rgba(240, 235, 220, 0.4); padding: 6px 10px; border-radius: 6px;">
                <strong>थाना संचालन अवलोकन:</strong> गरियाबंद के <em>देवभोग</em> एवं <em>पाण्डुका</em> तथा बिलासपुर के <em>पुलिस लाइन</em> ने प्रदेश में सर्वाधिक निरंतरता प्रदर्शित की है। औसत सहभागिता में पुलिस लाइन बिलासपुर (148.5) एवं बड़े डोंगर (56.3) का प्रदर्शन विशेष रूप से प्रभावी रहा है।
            </div>
        </div>

        <!-- Section 8: Action Plan (आगे की कार्यवाही) -->
        <div class="action-card">
            <div class="action-heading">
                आगे की कार्यवाही (Official Action Plan & Directives)
            </div>
            <ul class="action-list">
                <li><strong>संतुलित कार्यक्रम प्रारूप (Balanced Outreach Model):</strong> जिन जिलों में सूक्ष्म सत्रों (&lt;10 नागरिक) का अनुपात 30% से अधिक है, उन्हें साप्ताहिक हाट-बाजार, ग्राम पंचायतों और शैक्षणिक परिसरों में 50+ नागरिकों के सामूहिक सत्रों का अनुपात बढ़ाने की <strong>कार्यवाही</strong> सुनिश्चित करने हेतु निर्देशित किया जाए।</li>
                <li><strong>संभाग-स्तरीय समन्वय एवं समीक्षा:</strong> रायपुर कमिश्नरेट, नारायणपुर एवं महासमुंद के नोडल अधिकारियों के साथ समीक्षा बैठक आयोजित कर प्रत्येक थाने का न्यूनतम दैनिक लक्ष्य निर्धारित करने की <strong>कार्यवाही</strong> पूर्ण की जाए।</li>
                <li><strong>पोर्टल प्रविष्टि एवं डेटा गुणवत्ता आश्वासन:</strong> समस्त थाना प्रभारियों को पाबंद किया जाए कि कार्यक्रम समाप्ति के 2 घंटे के भीतर वास्तविक उपस्थिति संख्या, विषय एवं जिओ-टैग्ड फोटोग्राफ की पोर्टल एंट्री अनिवार्य <strong>कार्यवाही</strong> के रूप में सुनिश्चित करें।</li>
                <li><strong>विषय-वार फोकस ड्राइव:</strong> चालू अभियान के प्रमुख विषयों—डिजिटल अरेस्ट, जॉब/टास्क फ्रॉड एवं यूपीआई सुरक्षा—पर स्थानीय संवेदनशील केंद्रों (बैंक, सीएससी केंद्र, कॉलेज) में लक्षित ड्राइव संचालित करने की <strong>कार्यवाही</strong> की जाए।</li>
            </ul>
        </div>
    </div>
    <div class="footer">
        <div>साइबर जागृति अभियान - छत्तीसगढ़ पुलिस (सत्यमेव जयते)</div>
        <div>पृष्ठ 3 / 3 | Confidential & Official Administrative Use Only | जनरेशन: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}</div>
    </div>
</div>

</body>
</html>
"""

html_path = os.path.join(REPORTS_DIR, f"comprehensive_report_{latest_date}.html")
pdf_path = os.path.join(REPORTS_DIR, f"Cyber_Jagriti_Comprehensive_Report_{latest_date}.pdf")

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

print("Generated HTML successfully.")

cmd = [
    CHROME_BIN,
    "--headless",
    "--disable-gpu",
    "--no-pdf-header-footer",
    f"--print-to-pdf={pdf_path}",
    f"file://{html_path}"
]
res = subprocess.run(cmd, capture_output=True, text=True)
print("Chrome returncode:", res.returncode)
print("PDF size:", os.path.getsize(pdf_path), "bytes")
print(f"Saved comprehensive PDF to: {pdf_path}")
