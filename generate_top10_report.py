#!/usr/bin/env python3
"""
Cyber Jagriti Abhiyan - Top 10 Districts Attendance Categorized Report Generator
Generates pixel-perfect 100% audited Table 4 report for Top 10 Districts matching exact color scheme, fonts, and layout.
"""

import os
import sys
import json
import base64
import sqlite3
import subprocess
from datetime import datetime, timedelta
import shutil

from data_audit_agent import DataAuditAgent, get_audited_events_query_filter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "events.db")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
ARTIFACT_DIR = os.path.join(BASE_DIR, "reports")
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")

os.makedirs(REPORTS_DIR, exist_ok=True)

def get_chrome_bin():
    if os.environ.get("CHROME_BIN") and os.path.exists(os.environ["CHROME_BIN"]):
        return os.environ["CHROME_BIN"]
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    for bin_name in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"]:
        p = shutil.which(bin_name)
        if p:
            return p
    return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

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
        other = s[:-3]
        res = ""
        while len(other) > 2:
            res = "," + other[-2:] + res
            other = other[:-2]
        res = other + res + "," + last3
    return "-" + res if num < 0 else res

def generate_top10_report(target_date=None):
    # 1. Run Data Audit Agent
    audit_agent = DataAuditAgent(DB_PATH)
    audit_res = audit_agent.run_audit()
    filter_clause = get_audited_events_query_filter(audit_res)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Determine target date
    if not target_date:
        cur.execute(f"SELECT MAX(event_date) FROM events WHERE {filter_clause} AND event_date <= '2026-09-12'")
        max_dt = cur.fetchone()[0]
        target_date = max_dt or datetime.now().strftime("%Y-%m-%d")

    # Format date for header
    try:
        dt_obj = datetime.strptime(target_date, "%Y-%m-%d")
        weekdays_hi = ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"]
        months_hi = ["जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]
        formatted_date = f"{weekdays_hi[dt_obj.weekday()]} • {dt_obj.day} {months_hi[dt_obj.month - 1]} {dt_obj.year}"
        short_date_hi = f"{dt_obj.day:02d} {months_hi[dt_obj.month - 1]} {dt_obj.year}"
    except Exception:
        formatted_date = target_date
        short_date_hi = target_date

    # Base64 Logo
    logo_b64 = ""
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            logo_b64 = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

    # Query Top 10 Districts
    query = f"""
    SELECT 
        CASE 
            WHEN district_id IN (27, 34) OR LOWER(district_name_en) LIKE '%raipur%' THEN 'रायपुर'
            WHEN district_name_hi IS NOT NULL AND district_name_hi != '' THEN district_name_hi
            ELSE district_name_en
        END AS dist_name,
        COUNT(*) as total_events,
        SUM(CASE WHEN total_members >= 1 AND total_members <= 20 THEN 1 ELSE 0 END) as t_1_20,
        SUM(CASE WHEN total_members >= 21 AND total_members <= 50 THEN 1 ELSE 0 END) as t_21_50,
        SUM(CASE WHEN total_members >= 51 AND total_members <= 100 THEN 1 ELSE 0 END) as t_51_100,
        SUM(CASE WHEN total_members >= 101 AND total_members <= 500 THEN 1 ELSE 0 END) as t_101_500,
        SUM(CASE WHEN total_members > 500 THEN 1 ELSE 0 END) as t_gt_500,
        SUM(total_members) as total_reach
    FROM events
    WHERE {filter_clause}
    GROUP BY dist_name
    ORDER BY total_events DESC
    LIMIT 10
    """
    cur.execute(query)
    top10_rows = cur.fetchall()

    # Calculate Top 10 Summary KPIs
    tot_events_top10 = sum(r[1] for r in top10_rows)
    tot_1_20 = sum(r[2] for r in top10_rows)
    tot_21_50 = sum(r[3] for r in top10_rows)
    tot_51_100 = sum(r[4] for r in top10_rows)
    tot_101_500 = sum(r[5] for r in top10_rows)
    tot_gt_500 = sum(r[6] for r in top10_rows)
    tot_reach_top10 = sum(r[7] for r in top10_rows)

    pct_1_20 = (tot_1_20 / tot_events_top10 * 100) if tot_events_top10 > 0 else 0
    pct_21_50 = (tot_21_50 / tot_events_top10 * 100) if tot_events_top10 > 0 else 0
    pct_51_100 = (tot_51_100 / tot_events_top10 * 100) if tot_events_top10 > 0 else 0
    pct_101_500 = (tot_101_500 / tot_events_top10 * 100) if tot_events_top10 > 0 else 0
    pct_gt_500 = (tot_gt_500 / tot_events_top10 * 100) if tot_events_top10 > 0 else 0

    # Build HTML rows for Top 10
    rows_html = ""
    for rank, r in enumerate(top10_rows, 1):
        name_hi, tot, u20, u50, u100, u500, gt500, reach = r
        p1 = (u20 / tot * 100) if tot > 0 else 0
        p2 = (u50 / tot * 100) if tot > 0 else 0
        p3 = (u100 / tot * 100) if tot > 0 else 0
        p4 = (u500 / tot * 100) if tot > 0 else 0
        p5 = (gt500 / tot * 100) if tot > 0 else 0

        rows_html += f"""
        <tr>
            <td style="text-align: center; font-weight: 600; color: #475569;">{rank}</td>
            <td style="font-weight: 700; color: #0F172A;">{name_hi}</td>
            <td class="num">{format_indian(u20)}</td>
            <td class="num">{format_indian(u50)}</td>
            <td class="num">{format_indian(u100)}</td>
            <td class="num">{format_indian(u500)}</td>
            <td class="num">{format_indian(gt500)}</td>
            <td class="num bold-total">{format_indian(tot)}</td>
            <td>
                <div class="mix-bar">
                    <div class="seg seg-1" style="width: {p1:.1f}%;"></div>
                    <div class="seg seg-2" style="width: {p2:.1f}%;"></div>
                    <div class="seg seg-3" style="width: {p3:.1f}%;"></div>
                    <div class="seg seg-4" style="width: {p4:.1f}%;"></div>
                    <div class="seg seg-5" style="width: {p5:.1f}%;"></div>
                </div>
            </td>
        </tr>"""

    # Summary Total Row HTML
    total_row_html = f"""
    <tr class="total-row">
        <td style="text-align: center; font-weight: 700; color: #1E3A8A;">•</td>
        <td style="font-weight: 800; color: #1E3A8A;">शीर्ष 10 जिले योग</td>
        <td class="num bold-cell">{format_indian(tot_1_20)}</td>
        <td class="num bold-cell">{format_indian(tot_21_50)}</td>
        <td class="num bold-cell">{format_indian(tot_51_100)}</td>
        <td class="num bold-cell">{format_indian(tot_101_500)}</td>
        <td class="num bold-cell">{format_indian(tot_gt_500)}</td>
        <td class="num grand-total">{format_indian(tot_events_top10)}</td>
        <td>
            <div class="mix-bar">
                <div class="seg seg-1" style="width: {pct_1_20:.1f}%;"></div>
                <div class="seg seg-2" style="width: {pct_21_50:.1f}%;"></div>
                <div class="seg seg-3" style="width: {pct_51_100:.1f}%;"></div>
                <div class="seg seg-4" style="width: {pct_101_500:.1f}%;"></div>
                <div class="seg seg-5" style="width: {pct_gt_500:.1f}%;"></div>
            </div>
        </td>
    </tr>"""

    html_content = f"""<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<title>Cyber Jagriti Top 10 Districts Report</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Hind:wght@400;500;600;700&family=Poppins:wght@400;500;600;700;800&display=swap');

* {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}}

body {{
    background-color: #F1F5F9;
    font-family: 'Hind', 'Poppins', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #1E293B;
    padding: 16px;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}}

.report-container {{
    max-width: 1040px;
    margin: 0 auto;
    background: #FFFFFF;
    border-radius: 14px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    overflow: hidden;
    padding: 20px 24px;
}}

/* Top Dark Header */
.top-nav {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
    color: #FFFFFF;
    padding: 12px 20px;
    border-radius: 10px;
    margin-bottom: 20px;
}}

.nav-brand {{
    display: flex;
    align-items: center;
    gap: 12px;
}}

.nav-brand img {{
    height: 38px;
    width: auto;
    border-radius: 50%;
    background: #FFFFFF;
    padding: 2px;
}}

.nav-title {{
    font-size: 17px;
    font-weight: 700;
    letter-spacing: -0.2px;
}}

.nav-subtitle {{
    font-size: 13px;
    color: #94A3B8;
    font-weight: 500;
}}

.nav-date {{
    font-size: 13px;
    font-weight: 600;
    background: rgba(255, 255, 255, 0.12);
    padding: 6px 14px;
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.2);
}}

/* Title Section */
.section-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
}}

.title-wrap {{
    display: flex;
    align-items: center;
    gap: 12px;
}}

.badge-num {{
    background: #1E3A8A;
    color: #FFFFFF;
    font-family: 'Poppins', sans-serif;
    font-weight: 800;
    font-size: 14px;
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
}}

.section-title {{
    font-size: 18px;
    font-weight: 700;
    color: #0F172A;
}}

.pill-scope {{
    background: #E2E8F0;
    color: #334155;
    font-size: 12px;
    font-weight: 700;
    padding: 4px 14px;
    border-radius: 16px;
}}

/* KPI Cards Grid */
.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
    margin-bottom: 20px;
}}

.kpi-card {{
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 12px 14px;
    position: relative;
}}

.kpi-label {{
    font-size: 12px;
    font-weight: 600;
    color: #64748B;
    margin-bottom: 6px;
}}

.kpi-val {{
    font-family: 'Poppins', sans-serif;
    font-size: 22px;
    font-weight: 800;
    color: #0F172A;
    line-height: 1.1;
    margin-bottom: 8px;
}}

.kpi-progress {{
    height: 4px;
    background: #E2E8F0;
    border-radius: 2px;
    overflow: hidden;
    margin-bottom: 6px;
}}

.kpi-fill {{
    height: 100%;
    border-radius: 2px;
}}

.fill-1 {{ background: #94A3B8; }}
.fill-2 {{ background: #475569; }}
.fill-3 {{ background: #334155; }}
.fill-4 {{ background: #1E293B; }}
.fill-5 {{ background: #EA580C; }}

.kpi-pct {{
    font-family: 'Poppins', sans-serif;
    font-size: 12px;
    font-weight: 700;
    color: #475569;
}}

/* Table Styling */
.table-wrap {{
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 16px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}

thead tr {{
    background: #0F172A;
    color: #FFFFFF;
}}

th {{
    padding: 10px 12px;
    font-weight: 700;
    text-align: left;
    font-size: 12px;
    letter-spacing: 0.2px;
}}

th.num-header {{
    text-align: right;
}}

tbody tr {{
    border-bottom: 1px solid #E2E8F0;
    transition: background 0.15s ease;
}}

tbody tr:nth-child(even) {{
    background: #F8FAFC;
}}

td {{
    padding: 9px 12px;
    vertical-align: middle;
}}

td.num {{
    text-align: right;
    font-family: 'Poppins', sans-serif;
    font-weight: 600;
    color: #334155;
}}

td.bold-total {{
    font-family: 'Poppins', sans-serif;
    font-weight: 800;
    color: #1E3A8A;
    font-size: 14px;
}}

/* Stacked Bar */
.mix-bar {{
    height: 10px;
    width: 130px;
    background: #E2E8F0;
    border-radius: 5px;
    display: flex;
    overflow: hidden;
}}

.seg {{
    height: 100%;
}}

.seg-1 {{ background: #94A3B8; }}
.seg-2 {{ background: #475569; }}
.seg-3 {{ background: #334155; }}
.seg-4 {{ background: #1E293B; }}
.seg-5 {{ background: #EA580C; }}

/* Total Row */
tr.total-row {{
    background: #EEF2FF !important;
    border-top: 2px solid #1E3A8A;
    border-bottom: 2px solid #1E3A8A;
}}

td.bold-cell {{
    font-family: 'Poppins', sans-serif;
    font-weight: 800;
    color: #1E3A8A;
}}

td.grand-total {{
    font-family: 'Poppins', sans-serif;
    font-weight: 800;
    color: #1E3A8A;
    font-size: 15px;
}}

/* Footer & Legend */
.footer-note {{
    font-size: 11.5px;
    color: #64748B;
    margin-bottom: 12px;
    line-height: 1.4;
}}

.legend-bar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #F8FAFC;
    padding: 8px 14px;
    border-radius: 8px;
    border: 1px solid #E2E8F0;
    font-size: 12px;
}}

.legend-items {{
    display: flex;
    align-items: center;
    gap: 16px;
}}

.leg-item {{
    display: flex;
    align-items: center;
    gap: 6px;
    color: #334155;
    font-weight: 600;
}}

.leg-dot {{
    width: 10px;
    height: 10px;
    border-radius: 3px;
}}

.leg-text-right {{
    color: #64748B;
    font-size: 11.5px;
}}
</style>
</head>
<body>

<div class="report-container">

    <!-- Top Header Bar -->
    <div class="top-nav">
        <div class="nav-brand">
            {"<img src='" + logo_b64 + "' alt='Logo'>" if logo_b64 else ""}
            <div>
                <div class="nav-title">साइबर जागृति अभियान</div>
                <div class="nav-subtitle">उपस्थिति-श्रेणीबद्ध संचयी विवरण (शीर्ष 10 जिले)</div>
            </div>
        </div>
        <div class="nav-date">{formatted_date}</div>
    </div>

    <!-- Section Title Banner -->
    <div class="section-header">
        <div class="title-wrap">
            <div class="badge-num">01</div>
            <div class="section-title">तालिका 4: शीर्ष 10 जिलावार उपस्थिति-श्रेणीबद्ध कार्यक्रम ({short_date_hi} तक संचयी)</div>
        </div>
        <div class="pill-scope">शीर्ष 10 जिले</div>
    </div>

    <!-- KPI Grid Top -->
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">1 से 20 लोग</div>
            <div class="kpi-val">{format_indian(tot_1_20)}</div>
            <div class="kpi-progress"><div class="kpi-fill fill-1" style="width: {pct_1_20:.1f}%;"></div></div>
            <div class="kpi-pct">{pct_1_20:.2f}%</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">20 से 50 लोग</div>
            <div class="kpi-val">{format_indian(tot_21_50)}</div>
            <div class="kpi-progress"><div class="kpi-fill fill-2" style="width: {pct_21_50:.1f}%;"></div></div>
            <div class="kpi-pct">{pct_21_50:.2f}%</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">50 से 100 लोग</div>
            <div class="kpi-val">{format_indian(tot_51_100)}</div>
            <div class="kpi-progress"><div class="kpi-fill fill-3" style="width: {pct_51_100:.1f}%;"></div></div>
            <div class="kpi-pct">{pct_51_100:.2f}%</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">100 से 500 लोग</div>
            <div class="kpi-val">{format_indian(tot_101_500)}</div>
            <div class="kpi-progress"><div class="kpi-fill fill-4" style="width: {pct_101_500:.1f}%;"></div></div>
            <div class="kpi-pct">{pct_101_500:.2f}%</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">&gt;500 लोग</div>
            <div class="kpi-val">{format_indian(tot_gt_500)}</div>
            <div class="kpi-progress"><div class="kpi-fill fill-5" style="width: {pct_gt_500:.1f}%;"></div></div>
            <div class="kpi-pct">{pct_gt_500:.2f}%</div>
        </div>
    </div>

    <!-- Main Table 4 -->
    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th style="width: 32px; text-align: center;">#</th>
                    <th style="width: 22%;">जिला</th>
                    <th class="num-header" style="width: 10%;">1-20</th>
                    <th class="num-header" style="width: 10%;">20-50</th>
                    <th class="num-header" style="width: 10%;">50-100</th>
                    <th class="num-header" style="width: 10%;">100-500</th>
                    <th class="num-header" style="width: 8%;">&gt;500</th>
                    <th class="num-header" style="width: 14%;">कुल कार्यक्रम</th>
                    <th style="width: 16%;">मिश्रण</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
                {total_row_html}
            </tbody>
        </table>
    </div>

    <!-- Footer Note -->
    <div class="footer-note">
        <strong>नोट:</strong> यह तालिका 100% डेटा-ऑडिटेड डेटाबेस के अनुसार राज्य के <strong>शीर्ष 10 सर्वाधिक सक्रिय पुलिस जिलों</strong> के कुल <strong>{format_indian(tot_events_top10)}</strong> कार्यक्रमों तथा <strong>{format_indian(tot_reach_top10)}</strong> जागरूक नागरिकों का श्रेणीबद्ध संचयी विश्लेषण प्रदर्शित करती है।
    </div>

    <!-- Legend Footer Bar -->
    <div class="legend-bar">
        <div class="legend-items">
            <div class="leg-item"><div class="leg-dot fill-1"></div>1 से 20 लोग</div>
            <div class="leg-item"><div class="leg-dot fill-2"></div>20 से 50 लोग</div>
            <div class="leg-item"><div class="leg-dot fill-3"></div>50 से 100 लोग</div>
            <div class="leg-item"><div class="leg-dot fill-4"></div>100 से 500 लोग</div>
            <div class="leg-item"><div class="leg-dot fill-5"></div>&gt;500 लोग</div>
        </div>
        <div class="leg-text-right">दायरा = उस कार्यक्रम में उपस्थित लोगों की संख्या</div>
    </div>

</div>

</body>
</html>
"""

    # Save HTML
    html_path = os.path.join(REPORTS_DIR, f"top10_districts_report_{target_date}.html")
    pdf_path = os.path.join(REPORTS_DIR, f"Cyber_Jagriti_Top10_Districts_Report_{target_date}.pdf")
    png_path = os.path.join(ARTIFACT_DIR, "report_top10_districts.png")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[1/3] Generated Top 10 Districts audited HTML: {html_path}")

    # Render PDF
    pdf_rendered = False
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"file://{html_path}", wait_until="load")
            page.pdf(path=pdf_path, print_background=True, prefer_css_page_size=True)
            browser.close()
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            pdf_rendered = True
            print(f"[2/3] Rendered Top 10 Districts PDF via Playwright ({os.path.getsize(pdf_path):,} bytes) at: {pdf_path}")
    except Exception as e:
        print(f"[*] Playwright PDF notice: {e}")

    if not pdf_rendered:
        chrome_bin = get_chrome_bin()
        cmd_pdf = [
            chrome_bin,
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            f"file://{html_path}"
        ]
        subprocess.run(cmd_pdf, capture_output=True, text=True)
        if os.path.exists(pdf_path):
            print(f"[2/3] Rendered Top 10 Districts PDF via Chrome CLI ({os.path.getsize(pdf_path):,} bytes) at: {pdf_path}")

    # Render High-Resolution Preview PNG
    shot_done = False
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1100, "height": 950})
            page.goto(f"file://{html_path}", wait_until="load")
            page.screenshot(path=png_path, full_page=True)
            browser.close()
        if os.path.exists(png_path):
            shot_done = True
    except Exception:
        pass

    if not shot_done:
        chrome_bin = get_chrome_bin()
        cmd_shot = [
            chrome_bin,
            "--headless",
            "--disable-gpu",
            "--screenshot=" + png_path,
            "--window-size=1100,950",
            f"file://{html_path}"
        ]
        subprocess.run(cmd_shot, capture_output=True, text=True)
    print(f"[3/3] Generated Top 10 Districts preview screenshot: {png_path}")

    return pdf_path, png_path, target_date

if __name__ == "__main__":
    generate_top10_report()
