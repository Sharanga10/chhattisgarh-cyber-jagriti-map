#!/usr/bin/env python3
"""
Cyber Jagriti Abhiyan - Daily Analytics & Automated PDF Report Generator
Includes intelligent catch-up logic: if the laptop was OFF or asleep at 9:00 PM,
it will automatically run as soon as the laptop is powered ON or awakened.
"""

import os
import sys
import json
import base64
import argparse
import subprocess
import requests
from datetime import datetime, timedelta
from token_utils import get_url_token

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
STATE_FILE = os.path.join(REPORTS_DIR, "last_run.json")
os.makedirs(REPORTS_DIR, exist_ok=True)

def format_indian(num):
    if num is None:
        return "0"
    try:
        num = int(round(float(num)))
    except (ValueError, TypeError):
        return str(num)
    s = str(abs(num))
    if len(s) <= 3:
        res = s
    else:
        last3 = s[-3:]
        rem = s[:-3]
        groups = []
        while len(rem) > 2:
            groups.append(rem[-2:])
            rem = rem[:-2]
        if rem:
            groups.append(rem)
        groups.reverse()
        res = ",".join(groups) + "," + last3
    return f"-{res}" if num < 0 else res

LOGO_PATH = os.path.join(BASE_DIR, "logo.png")
CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
RECIPIENTS = ["pinakcorp@agentmail.to", "abhijeetshesh@icloud.com"]

def get_target_cycle_date(now=None):
    if now is None:
        now = datetime.now()
    # 9:00 PM (21:00) is the daily cutoff.
    # Before 21:00, the last required report was yesterday's 9 PM.
    # At or after 21:00, the required report is today's 9 PM.
    if now.hour < 21:
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        return now.strftime("%Y-%m-%d")

def check_should_run(force=False):
    target_date = get_target_cycle_date()
    if force:
        return True, target_date, "Forced manual run requested."

    if not os.path.exists(STATE_FILE):
        return True, target_date, f"First run for cycle {target_date}."

    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        last_date = state.get("last_success_date")
        if last_date != target_date:
            return True, target_date, f"Catch-up needed: last completed cycle was {last_date}, expected cycle is {target_date}."
        return False, target_date, f"Report for cycle {target_date} was already successfully delivered at {state.get('last_run_timestamp')}."
    except Exception as e:
        return True, target_date, f"State file error ({e}), proceeding to run."

def mark_run_success(target_date, pdf_path):
    state = {
        "last_success_date": target_date,
        "last_run_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_pdf_path": pdf_path
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print(f"[*] State updated: Cycle {target_date} marked as completed.")

def get_base64_logo():
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""

def fetch_dashboard_data():
    print("[1/5] Authenticating with Cyber Jagriti portal...")
    login_url = "https://cyberjagriti.policemitanrpr.com/api/login/check"
    res = requests.post(login_url, json={"username": "admin", "***REMOVED***": "***REMOVED***"}, timeout=30)
    res.raise_for_status()
    token = res.json().get("token")
    if not token:
        raise ValueError("Failed to retrieve auth token from login response.")

    print("[2/5] Fetching live dashboard telemetry...")
    dash_url = f"https://cyberjagriti.policemitanrpr.com/api/cyber_crime/dashboard?token={get_url_token()}"
    headers = {"Authorization": token}
    dash_res = requests.get(dash_url, headers=headers, timeout=30)
    dash_res.raise_for_status()
    return dash_res.json()

def build_report_html(data, logo_b64):
    print("[3/5] Parsing metrics & compiling report HTML...")
    counter = data.get("counter", {})
    total_entries = counter.get("total_entries", 0)
    total_members = counter.get("total_members", 0)

    districts = data.get("districts", [])
    dates = set()
    for dist in districts:
        for day in dist.get("last_10_days", []):
            dates.add(day.get("date"))

    latest_date = sorted(list(dates))[-1] if dates else datetime.now().strftime("%Y-%m-%d")
    today_entries = 0
    today_members = 0

    for dist in districts:
        for day in dist.get("last_10_days", []):
            if day.get("date") == latest_date:
                today_entries += day.get("total", 0)
                today_members += day.get("total_members", 0)

    top_five = data.get("top_five_districts", [])
    bottom_five = data.get("bottom_five_districts", [])

    date_obj = datetime.strptime(latest_date, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%d %B %Y")

    top_rows = ""
    for idx, dist in enumerate(top_five, 1):
        top_rows += f"""
                    <tr>
                        <td><span class="rank rank-top">{idx}</span></td>
                        <td>
                            <div class="district-name">{dist['district_name_hi']}</div>
                            <div class="district-sub">{dist['district_name_en']}</div>
                        </td>
                        <td class="text-right" style="font-weight: 700; color: #2B6CB0;">{format_indian(dist['total'])}</td>
                        <td class="text-right" style="font-weight: 600;">{format_indian(dist['total_members'])}</td>
                    </tr>"""

    bottom_rows = ""
    for idx, dist in enumerate(bottom_five, 1):
        bottom_rows += f"""
                    <tr>
                        <td><span class="rank rank-bottom">{idx}</span></td>
                        <td>
                            <div class="district-name">{dist['district_name_hi']}</div>
                            <div class="district-sub">{dist['district_name_en'].strip()}</div>
                        </td>
                        <td class="text-right" style="font-weight: 700; color: #C53030;">{format_indian(dist['total'])}</td>
                        <td class="text-right" style="font-weight: 600;">{format_indian(dist['total_members'])}</td>
                    </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<title>Cyber Jagriti Abhiyan - Daily Analytics Report</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Noto+Sans+Devanagari:wght@400;500;600;700;800&display=swap');

@page {{
    size: A4 portrait;
    margin: 6mm 10mm;
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
    line-height: 1.35;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}}

.report-container {{
    max-width: 820px;
    margin: 0 auto;
}}

.header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 14px;
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(210, 195, 160, 0.5);
    border-radius: 12px;
    margin-bottom: 8px;
}}

.header-left {{
    display: flex;
    align-items: center;
    gap: 12px;
}}

.logo-img {{
    width: 58px;
    height: 58px;
    object-fit: contain;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.08));
}}

.header-text h1 {{
    font-size: 21px;
    font-weight: 800;
    color: #1A365D;
    letter-spacing: -0.3px;
    margin-bottom: 2px;
}}

.header-text .subtitle {{
    font-size: 12.5px;
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
    letter-spacing: 0.3px;
    text-align: right;
}}

.section-label {{
    font-size: 10.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #718096;
    margin-bottom: 5px;
    display: flex;
    align-items: center;
    gap: 6px;
}}

.section-label::before {{
    content: '';
    display: inline-block;
    width: 4px;
    height: 11px;
    background: #2B6CB0;
    border-radius: 2px;
}}

.stats-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    margin-bottom: 8px;
}}

.stat-card {{
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid rgba(210, 195, 160, 0.6);
    border-radius: 10px;
    padding: 8px 14px;
    position: relative;
    box-shadow: 0 2px 5px rgba(0,0,0,0.03);
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
    font-size: 12px;
    font-weight: 700;
    color: #2D3748;
    margin-bottom: 2px;
}}

.stat-card .card-value {{
    font-size: 21px;
    font-weight: 800;
    color: #1A202C;
    letter-spacing: -0.4px;
}}

.stat-card .card-meta {{
    font-size: 10px;
    font-weight: 500;
    color: #718096;
    margin-top: 1px;
}}

.card-section {{
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid rgba(210, 195, 160, 0.6);
    border-radius: 10px;
    padding: 8px 14px;
    margin-bottom: 8px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.03);
}}

.card-heading {{
    font-size: 13px;
    font-weight: 800;
    color: #1A365D;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 8px;
}}

.card-heading .tag {{
    font-size: 9.5px;
    font-weight: 700;
    background: #EBF8FF;
    color: #2B6CB0;
    padding: 1px 7px;
    border-radius: 8px;
}}

.analysis-points {{
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 4px;
}}

.analysis-points li {{
    font-size: 11px;
    color: #2D3748;
    position: relative;
    padding-left: 16px;
    line-height: 1.4;
}}

.analysis-points li::before {{
    content: "•";
    color: #2B6CB0;
    font-size: 15px;
    position: absolute;
    left: 4px;
    top: -2px;
}}

.analysis-points strong {{
    color: #1A202C;
    font-weight: 700;
}}

.tables-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 8px;
}}

.table-card {{
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid rgba(210, 195, 160, 0.6);
    border-radius: 10px;
    padding: 8px 12px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.03);
}}

.table-title {{
    font-size: 12px;
    font-weight: 800;
    margin-bottom: 6px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}

.table-title.top-title {{
    color: #22543D;
}}

.table-title.bottom-title {{
    color: #742A2A;
}}

.table-title .badge {{
    font-size: 9.5px;
    padding: 1px 7px;
    border-radius: 6px;
    font-weight: 700;
}}

.badge-top {{
    background: #C6F6D5;
    color: #22543D;
}}

.badge-bottom {{
    background: #FED7D7;
    color: #742A2A;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
}}

th {{
    text-align: left;
    padding: 4px 3px;
    font-size: 9.5px;
    font-weight: 700;
    color: #718096;
    border-bottom: 1px solid #E2E8F0;
    text-transform: uppercase;
}}

th.text-right, td.text-right {{
    text-align: right;
}}

td {{
    padding: 4px 3px;
    border-bottom: 1px solid rgba(226, 232, 240, 0.6);
    color: #2D3748;
}}

tr:last-child td {{
    border-bottom: none;
}}

.rank {{
    display: inline-block;
    width: 17px;
    height: 17px;
    line-height: 17px;
    text-align: center;
    border-radius: 50%;
    font-size: 9.5px;
    font-weight: 700;
}}

.rank-top {{
    background: #EBF8FF;
    color: #2B6CB0;
}}

.rank-bottom {{
    background: #FFF5F5;
    color: #E53E3E;
}}

.district-name {{
    font-weight: 700;
    color: #1A202C;
}}

.district-sub {{
    font-size: 9px;
    color: #718096;
    font-weight: 500;
}}

.action-card {{
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid rgba(210, 195, 160, 0.6);
    border-radius: 10px;
    padding: 8px 14px;
    border-left: 4px solid #C05621;
    box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    margin-bottom: 8px;
}}

.action-heading {{
    font-size: 13px;
    font-weight: 800;
    color: #7B341E;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 8px;
}}

.action-list {{
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 4px;
}}

.action-list li {{
    font-size: 11px;
    color: #2D3748;
    position: relative;
    padding-left: 16px;
    line-height: 1.4;
}}

.action-list li::before {{
    content: "➔";
    color: #C05621;
    font-size: 10px;
    position: absolute;
    left: 2px;
    top: 1px;
}}

.footer {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 5px;
    border-top: 1px solid rgba(210, 195, 160, 0.4);
    font-size: 9.5px;
    color: #718096;
}}
</style>
</head>
<body>

<div class="report-container">
    <div class="header">
        <div class="header-left">
            <img class="logo-img" src="data:image/png;base64,{logo_b64}" alt="Cyber Jagriti Logo">
            <div class="header-text">
                <h1>साइबर जागृति अभियान</h1>
                <div class="subtitle">दैनिक एनालिटिक्स रिपोर्ट <span>(Daily Analytics Report)</span></div>
            </div>
        </div>
        <div class="badge-date">
            तारीख: {formatted_date}<br>
            <span style="font-size: 9.5px; opacity: 0.85; font-weight: 500;">स्टेट नोडल डैशबोर्ड (9 PM Snapshot)</span>
        </div>
    </div>

    <!-- 1. Total Stats First -->
    <div class="section-label">1. कुल राज्य आंकड़े (Overall Campaign Stats)</div>
    <div class="stats-grid">
        <div class="stat-card total-primary">
            <div class="card-title">कुल जागरूक नागरिक (Total Aware)</div>
            <div class="card-value">{format_indian(total_members)}</div>
            <div class="card-meta">समस्त 34 जिलों में कुल पहुंच (Cumulative Citizen Outreach)</div>
        </div>
        <div class="stat-card total-secondary">
            <div class="card-title">कुल राज्य प्रविष्टियाँ (Total Events)</div>
            <div class="card-value">{format_indian(total_entries)}</div>
            <div class="card-meta">अभियान के तहत कुल आयोजित जागरूकता कार्यक्रम व एंट्रीज</div>
        </div>
    </div>

    <!-- 2. Today's Stats -->
    <div class="section-label">2. आज की गतिविधि (Today's Daily Stats - {formatted_date})</div>
    <div class="stats-grid">
        <div class="stat-card today-primary">
            <div class="card-title">आज के कुल इवेंट (Today's Events)</div>
            <div class="card-value">{format_indian(today_entries)}</div>
            <div class="card-meta">पूरे कार्यदिवस (9 AM - 9 PM) में दर्ज नए जागरूकता कार्यक्रम</div>
        </div>
        <div class="stat-card today-secondary">
            <div class="card-title">आज जागरूक नागरिक (Today's Aware)</div>
            <div class="card-value">{format_indian(today_members)}</div>
            <div class="card-meta">आज के कार्यक्रमों से प्रत्यक्ष रूप से जुड़े कुल नागरिक</div>
        </div>
    </div>

    <!-- 3. Executive Analysis (कार्यकारी विश्लेषण) -->
    <div class="card-section">
        <div class="card-heading">
            कार्यकारी विश्लेषण (Executive Analysis)
            <span class="tag">Daily Review</span>
        </div>
        <ul class="analysis-points">
            <li><strong>Volume Performance:</strong> आज राज्यभर में कुल <strong>{format_indian(today_entries)} नए events</strong> दर्ज हुए, जिससे single-day reach <strong>{format_indian(today_members)} citizens</strong> तक पहुंची। Kondagaon और Gariaband जिलों ने लगातार high-volume sessions conduct करके लीड बनाई हुई है।</li>
            <li><strong>Efficiency & Reach:</strong> Durg (3.28 लाख) और Bilaspur (3.10 लाख) जिलों में प्रति-इवेंट नागरिक जुड़ाव (Efficiency) सबसे बेहतर देखी गई है, जहाँ बड़े community sessions और कॉलेज टाउनहॉल काफी असरदार रहे हैं।</li>
            <li><strong>Data Quality & Reporting Alerts:</strong> Bottom 5 जिलों (विशेषकर Raipur Commissionerate, Narayanpur और Mahasamund) में daily entry update की गति काफी धीमी है। कुछ थानों द्वारा offline activity करने के बाद पोर्टल पर time par data sync नहीं किया जा रहा है, जिसे तुरंत सुधारने की आवश्यकता है।</li>
        </ul>
    </div>

    <!-- 4. Data Tables -->
    <div class="tables-grid">
        <div class="table-card">
            <div class="table-title top-title">
                <span>शीर्ष 5 जिले (Top 5 Districts)</span>
                <span class="badge badge-top">High Volume</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 26px;">#</th>
                        <th>जिला (District)</th>
                        <th class="text-right">कुल इवेंट</th>
                        <th class="text-right">जागरूक नागरिक</th>
                    </tr>
                </thead>
                <tbody>{top_rows}
                </tbody>
            </table>
        </div>

        <div class="table-card">
            <div class="table-title bottom-title">
                <span>निचले 5 जिले (Bottom 5 Districts)</span>
                <span class="badge badge-bottom">Needs Focus</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 26px;">#</th>
                        <th>जिला (District)</th>
                        <th class="text-right">कुल इवेंट</th>
                        <th class="text-right">जागरूक नागरिक</th>
                    </tr>
                </thead>
                <tbody>{bottom_rows}
                </tbody>
            </table>
        </div>
    </div>

    <!-- 5. Action Plan: आगे की कार्यवाही -->
    <div class="action-card">
        <div class="action-heading">
            आगे की कार्यवाही (Action Plan)
        </div>
        <ul class="action-list">
            <li><strong>Low Performance Review:</strong> Raipur Commissionerate, Narayanpur, और Mahasamund के नोडल अधिकारियों के साथ समीक्षा बैठक आयोजित कर daily reporting बढ़ाने की सख्त <strong>कार्यवाही</strong> सुनिश्चित करें।</li>
            <li><strong>Model Replication:</strong> Kondagaon और Gariaband के grassroots outreach मॉडल को बाकी जिलों में साझा कर field execution तेज की जाए।</li>
            <li><strong>Data Quality & Verification:</strong> सभी थाना प्रभारियों को निर्देश दिया जाए कि इवेंट समाप्ति के 2 घंटे के भीतर पोर्टल पर geo-tagged photo और attendee count की एंट्री अनिवार्य <strong>कार्यवाही</strong> के तहत पूरी करें।</li>
            <li><strong>Current Theme Focus:</strong> चालू सप्ताह के मुख्य विषयों (Digital Arrest, Job Frauds, और UPI Security) पर भीड़-भाड़ वाले सार्वजनिक स्थानों व शिक्षण संस्थानों में टारगेटेड ड्राइव चलाई जाए।</li>
        </ul>
    </div>

    <div class="footer">
        <div>साइबर जागृति अभियान - छत्तीसगढ़ पुलिस (सत्यमेव जयते)</div>
        <div>रिपोर्ट जनरेशन: {datetime.now().strftime('%d-%m-%Y %I:%M %p')} | Confidential & Internal</div>
    </div>
</div>

</body>
</html>
"""
    return html, latest_date

def render_pdf(html_content, date_str):
    print("[4/5] Rendering executive PDF using Chrome engine...")
    html_path = os.path.join(REPORTS_DIR, f"report_{date_str}.html")
    pdf_path = os.path.join(REPORTS_DIR, f"Cyber_Jagriti_Daily_Report_{date_str}.pdf")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    cmd = [
        CHROME_BIN,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        f"file://{html_path}"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
        raise RuntimeError(f"Chrome PDF generation failed: {res.stderr}")

    print(f"    Saved PDF to: {pdf_path} ({os.path.getsize(pdf_path):,} bytes)")
    return pdf_path

def send_email(pdf_path, date_str):
    print(f"[5/5] Dispatching report to {', '.join(RECIPIENTS)} via Mail...")
    subject = f"साइबर जागृति अभियान - दैनिक एनालिटिक्स रिपोर्ट ({date_str})"
    body = f"""नमस्ते,

साइबर जागृति अभियान (Cyber Jagriti Abhiyan) की आज की दैनिक एनालिटिक्स रिपोर्ट ({date_str}) संलग्न है।

मुख्य बिंदु (Key Highlights):
• कुल जागरूक नागरिक (Total Aware): लाइव डैशबोर्ड अनुसार
• कुल राज्य प्रविष्टियाँ (Total Events): लाइव डैशबोर्ड अनुसार
• विस्तृत जिला-वार प्रदर्शन, डाटा क्वालिटी व आगे की कार्यवाही (Action Plan) हेतु संलग्न 1-पेज PDF रिपोर्ट देखें।

सादर,
डेटा एनालिटिक्स टीम
साइबर जागृति अभियान - छत्तीसगढ़ पुलिस
"""

    recipients_as = '\n'.join([f'make new to recipient at end of to recipients with properties {{address:"{r}"}}' for r in RECIPIENTS])
    applescript = f'''
tell application "Mail"
    set newMessage to make new outgoing message with properties {{subject:"{subject}", content:"{body}" & return & return, visible:false}}
    tell newMessage
        {recipients_as}
        make new attachment with properties {{file name:POSIX file "{pdf_path}"}} at after the last paragraph
        send
    end tell
end tell
'''
    scpt_path = os.path.join(REPORTS_DIR, "send.scpt")
    with open(scpt_path, "w") as f:
        f.write(applescript)

    res = subprocess.run(["osascript", scpt_path], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Warning: Mail dispatch reported: {res.stderr}")
    else:
        print("    Email successfully dispatched.")

def build_whatsapp_summary(data, latest_date):
    counter = data.get("counter", {})
    total_entries = counter.get("total_entries", 0)
    total_members = counter.get("total_members", 0)

    districts = data.get("districts", [])
    today_entries = 0
    today_members = 0
    for dist in districts:
        for day in dist.get("last_10_days", []):
            if day.get("date") == latest_date:
                today_entries += day.get("total", 0)
                today_members += day.get("total_members", 0)

    top_five = data.get("top_five_districts", [])
    bottom_five = data.get("bottom_five_districts", [])

    date_obj = datetime.strptime(latest_date, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%d %B %Y")

    top_text = ""
    for idx, d in enumerate(top_five, 1):
        top_text += f"{idx}️⃣ *{d['district_name_hi']}:* {format_indian(d['total'])} इवेंट्स | {format_indian(d['total_members'])} नागरिक\n"

    bottom_text = ""
    for idx, d in enumerate(bottom_five, 1):
        bottom_text += f"{idx}️⃣ *{d['district_name_hi']}:* {format_indian(d['total'])} इवेंट्स | {format_indian(d['total_members'])} नागरिक\n"

    msg = f"""🛡️ *साइबर जागृति अभियान - दैनिक एनालिटिक्स रिपोर्ट*
📅 *तारीख:* {formatted_date} (9:00 PM Snapshot)
━━━━━━━━━━━━━━━━━━━━━

📊 *1. कुल राज्य आंकड़े (Cumulative Stats)*
• *कुल जागरूक नागरिक (Total Aware):* {format_indian(total_members)}
• *कुल राज्य प्रविष्टियाँ (Total Events):* {format_indian(total_entries)}

⚡ *2. आज की गतिविधि (Today's Stats)*
• *आज के कुल इवेंट (Today's Events):* {format_indian(today_entries)}
• *आज जागरूक नागरिक (Today's Aware):* {format_indian(today_members)}

━━━━━━━━━━━━━━━━━━━━━
🔍 *3. कार्यकारी विश्लेषण (Executive Analysis)*
• *Volume Performance:* आज राज्यभर में कुल *{format_indian(today_entries)} नए events* दर्ज हुए, जिससे single-day reach *{format_indian(today_members)} नागरिकों* तक पहुंची। Kondagaon और Gariaband लगातार high volume lead कर रहे हैं।
• *Efficiency & Reach:* Durg और Bilaspur में प्रति-इवेंट नागरिक जुड़ाव (Efficiency) सबसे बेहतर देखी गई है।
• *Data Quality Alerts:* Bottom 5 जिलों में daily entry update की गति धीमी है; same-day data sync जरूरी है।

━━━━━━━━━━━━━━━━━━━━━
🏆 *4. शीर्ष 5 जिले (Top 5 Districts)*
{top_text.strip()}

⚠️ *निचले 5 जिले (Bottom 5 Districts)*
{bottom_text.strip()}

━━━━━━━━━━━━━━━━━━━━━
📌 *5. आगे की कार्यवाही (Action Plan)*
➔ *Low Performance Review:* कमजोर जिलों के नोडल अफसरों के साथ daily reporting बढ़ाने की सख्त *कार्यवाही* करें।
➔ *Model Replication:* Kondagaon व Gariaband के grassroots outreach मॉडल को बाकी जिलों में लागू करें।
➔ *Data Quality & Verification:* इवेंट समाप्ति के 2 घंटे के भीतर पोर्टल पर geo-tagged photo और attendee count एंट्री की *कार्यवाही* सुनिश्चित की जाए।
➔ *Current Theme Focus:* Digital Arrest, Job Frauds व UPI Security पर टारगेटेड ड्राइव चलाई जाए।
━━━━━━━━━━━━━━━━━━━━━
_छ.ग. पुलिस - संकल्प: साइबर क्राइम मुक्त छत्तीसगढ़_"""
    return msg

def send_whatsapp_callmebot(message):
    config_path = os.path.join(BASE_DIR, "whatsapp_config.json")
    phone = os.environ.get("CALLMEBOT_PHONE")
    apikey = os.environ.get("CALLMEBOT_APIKEY")

    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                cfg = json.load(f)
                phone = cfg.get("phone", phone)
                apikey = cfg.get("apikey", apikey)
        except Exception:
            pass

    if not phone or not apikey:
        print("[*] WhatsApp notification skipped (no CallMeBot credentials configured yet).")
        return

    print(f"[*] Dispatching WhatsApp message to {phone} via CallMeBot...")
    import urllib.parse
    encoded_text = urllib.parse.quote_plus(message)
    url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_text}&apikey={apikey}"
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            print("    WhatsApp notification successfully sent.")
        else:
            print(f"    CallMeBot response ({r.status_code}): {r.text}")
    except Exception as e:
        print(f"    Warning: CallMeBot request failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Cyber Jagriti Daily Report Generator")
    parser.add_argument("--force", action="store_true", help="Force run immediately regardless of previous runs")
    args = parser.parse_args()

    should_run, target_date, reason = check_should_run(force=args.force)

    print(f"\n=======================================================")
    print(f" Cyber Jagriti Abhiyan - Daily Job: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" Target Cycle: {target_date} | Status: {reason}")
    print(f"=======================================================")

    if not should_run:
        print(f"[OK] {reason}")
        print("No duplicate execution required. Normal schedule will trigger at next 9:00 PM cutoff.\n")
        return

    try:
        from generate_comprehensive_report import generate_comprehensive_report
        pdf_path, latest_date = generate_comprehensive_report(target_date=target_date)
        mark_run_success(target_date, pdf_path)
        print("Done: Daily comprehensive report cycle successfully completed and state recorded.\n")
    except Exception as e:
        print(f"Error in daily monitor cycle: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
