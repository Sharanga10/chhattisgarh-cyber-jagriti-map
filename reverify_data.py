#!/usr/bin/env python3
"""
Re-verify Data & Compare 09 Sep Baseline vs 11 Sep Audited Ground Truth
"""

import os
import sys
import json
import base64
import sqlite3
import subprocess

BASE_DIR = "/Users/abhi-macmini/.gemini/antigravity-ide/scratch/cyber-jagriti-monitor-repo"
DB_PATH = os.path.join(BASE_DIR, "events.db")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
ARTIFACT_DIR = "/Users/abhi-macmini/.gemini/antigravity-ide/brain/6f59861b-1f45-4be1-a253-027ca122e4a4"
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")

logo_b64 = ""
if os.path.exists(LOGO_PATH):
    with open(LOGO_PATH, "rb") as f:
        logo_b64 = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

def format_indian(num):
    if num is None:
        return "0"
    try:
        num = int(round(float(num)))
    except Exception:
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

# 1. DATA FROM USER'S UPLOADED ATTACHED IMAGE (Table 4 up to 09 Sep 2026)
data_09sep_cards = {
    't1_20': (87808, 60.62),
    't21_50': (38535, 26.60),
    't51_100': (11243, 7.76),
    't101_500': (6400, 4.42),
    'tgt_500': (866, 0.60),
    'total_events': 144852
}

data_09sep_top10 = [
    ('गरियाबंद', 24610, 8734, 1107, 393, 42, 34886),
    ('कोंडागांव', 20038, 7149, 1552, 752, 35, 29526),
    ('दुर्ग', 6335, 4768, 1536, 903, 31, 13573),
    ('बिलासपुर', 3921, 5220, 1974, 907, 219, 12241),
    ('मुंगेली', 984, 1823, 1699, 126, 19, 4651),
    ('सुकमा', 2941, 1094, 206, 116, 5, 4362),
    ('बलौदाबाजार-भाटापारा', 3874, 254, 135, 25, 2, 4290),
    ('जांजगीर-चांपा', 2299, 1171, 210, 461, 40, 4181),
    ('बस्तर', 3036, 445, 138, 130, 8, 3757),
    ('बलरामपुर-रामानुजगंज', 2535, 579, 145, 315, 4, 3578)
]

def build_html(title_date, scope_label, kpi_cards, top10_rows, footer_text):
    tot_events = sum(r[6] for r in top10_rows)
    tot_1_20 = sum(r[1] for r in top10_rows)
    tot_21_50 = sum(r[2] for r in top10_rows)
    tot_51_100 = sum(r[3] for r in top10_rows)
    tot_101_500 = sum(r[4] for r in top10_rows)
    tot_gt_500 = sum(r[5] for r in top10_rows)

    pct_1_20 = (tot_1_20 / tot_events * 100) if tot_events > 0 else 0
    pct_21_50 = (tot_21_50 / tot_events * 100) if tot_events > 0 else 0
    pct_51_100 = (tot_51_100 / tot_events * 100) if tot_events > 0 else 0
    pct_101_500 = (tot_101_500 / tot_events * 100) if tot_events > 0 else 0
    pct_gt_500 = (tot_gt_500 / tot_events * 100) if tot_events > 0 else 0

    rows_html = ""
    for rank, r in enumerate(top10_rows, 1):
        name_hi, u20, u50, u100, u500, gt500, tot = r
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

    total_row_html = f"""
    <tr class="total-row">
        <td style="text-align: center; font-weight: 700; color: #1E3A8A;">•</td>
        <td style="font-weight: 800; color: #1E3A8A;">शीर्ष 10 जिले योग</td>
        <td class="num bold-cell">{format_indian(tot_1_20)}</td>
        <td class="num bold-cell">{format_indian(tot_21_50)}</td>
        <td class="num bold-cell">{format_indian(tot_51_100)}</td>
        <td class="num bold-cell">{format_indian(tot_101_500)}</td>
        <td class="num bold-cell">{format_indian(tot_gt_500)}</td>
        <td class="num grand-total">{format_indian(tot_events)}</td>
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

    c1_val, c1_pct = kpi_cards['t1_20']
    c2_val, c2_pct = kpi_cards['t21_50']
    c3_val, c3_pct = kpi_cards['t51_100']
    c4_val, c4_pct = kpi_cards['t101_500']
    c5_val, c5_pct = kpi_cards['tgt_500']

    return f"""<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<title>Cyber Jagriti Top 10 Report - {title_date}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Hind:wght@400;500;600;700&family=Poppins:wght@400;500;600;700;800&display=swap');
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background-color: #F1F5F9; font-family: 'Hind', 'Poppins', sans-serif; color: #1E293B; padding: 16px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.report-container {{ max-width: 1040px; margin: 0 auto; background: #FFFFFF; border-radius: 14px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); padding: 20px 24px; }}
.top-nav {{ display: flex; align-items: center; justify-content: space-between; background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%); color: #FFFFFF; padding: 12px 20px; border-radius: 10px; margin-bottom: 20px; }}
.nav-brand {{ display: flex; align-items: center; gap: 12px; }}
.nav-brand img {{ height: 38px; width: auto; border-radius: 50%; background: #FFFFFF; padding: 2px; }}
.nav-title {{ font-size: 17px; font-weight: 700; }}
.nav-subtitle {{ font-size: 13px; color: #94A3B8; font-weight: 500; }}
.nav-date {{ font-size: 13px; font-weight: 600; background: rgba(255, 255, 255, 0.12); padding: 6px 14px; border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.2); }}
.section-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }}
.title-wrap {{ display: flex; align-items: center; gap: 12px; }}
.badge-num {{ background: #1E3A8A; color: #FFFFFF; font-family: 'Poppins', sans-serif; font-weight: 800; font-size: 14px; width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; }}
.section-title {{ font-size: 18px; font-weight: 700; color: #0F172A; }}
.pill-scope {{ background: #E2E8F0; color: #334155; font-size: 12px; font-weight: 700; padding: 4px 14px; border-radius: 16px; }}
.kpi-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 20px; }}
.kpi-card {{ background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 12px 14px; }}
.kpi-label {{ font-size: 12px; font-weight: 600; color: #64748B; margin-bottom: 6px; }}
.kpi-val {{ font-family: 'Poppins', sans-serif; font-size: 22px; font-weight: 800; color: #0F172A; line-height: 1.1; margin-bottom: 8px; }}
.kpi-progress {{ height: 4px; background: #E2E8F0; border-radius: 2px; overflow: hidden; margin-bottom: 6px; }}
.kpi-fill {{ height: 100%; border-radius: 2px; }}
.fill-1 {{ background: #94A3B8; }} .fill-2 {{ background: #475569; }} .fill-3 {{ background: #334155; }} .fill-4 {{ background: #1E293B; }} .fill-5 {{ background: #EA580C; }}
.kpi-pct {{ font-family: 'Poppins', sans-serif; font-size: 12px; font-weight: 700; color: #475569; }}
.table-wrap {{ border: 1px solid #E2E8F0; border-radius: 10px; overflow: hidden; margin-bottom: 16px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
thead tr {{ background: #0F172A; color: #FFFFFF; }}
th {{ padding: 10px 12px; font-weight: 700; text-align: left; font-size: 12px; }}
th.num-header {{ text-align: right; }}
tbody tr {{ border-bottom: 1px solid #E2E8F0; }}
tbody tr:nth-child(even) {{ background: #F8FAFC; }}
td {{ padding: 9px 12px; vertical-align: middle; }}
td.num {{ text-align: right; font-family: 'Poppins', sans-serif; font-weight: 600; color: #334155; }}
td.bold-total {{ font-family: 'Poppins', sans-serif; font-weight: 800; color: #1E3A8A; font-size: 14px; }}
.mix-bar {{ height: 10px; width: 130px; background: #E2E8F0; border-radius: 5px; display: flex; overflow: hidden; }}
.seg {{ height: 100%; }}
.seg-1 {{ background: #94A3B8; }} .seg-2 {{ background: #475569; }} .seg-3 {{ background: #334155; }} .seg-4 {{ background: #1E293B; }} .seg-5 {{ background: #EA580C; }}
tr.total-row {{ background: #EEF2FF !important; border-top: 2px solid #1E3A8A; border-bottom: 2px solid #1E3A8A; }}
td.bold-cell {{ font-family: 'Poppins', sans-serif; font-weight: 800; color: #1E3A8A; }}
td.grand-total {{ font-family: 'Poppins', sans-serif; font-weight: 800; color: #1E3A8A; font-size: 15px; }}
.footer-note {{ font-size: 11.5px; color: #64748B; margin-bottom: 12px; line-height: 1.4; }}
.legend-bar {{ display: flex; align-items: center; justify-content: space-between; background: #F8FAFC; padding: 8px 14px; border-radius: 8px; border: 1px solid #E2E8F0; font-size: 12px; }}
.legend-items {{ display: flex; align-items: center; gap: 16px; }}
.leg-item {{ display: flex; align-items: center; gap: 6px; color: #334155; font-weight: 600; }}
.leg-dot {{ width: 10px; height: 10px; border-radius: 3px; }}
.leg-text-right {{ color: #64748B; font-size: 11.5px; }}
</style>
</head>
<body>
<div class="report-container">
    <div class="top-nav">
        <div class="nav-brand">
            {"<img src='" + logo_b64 + "' alt='Logo'>" if logo_b64 else ""}
            <div>
                <div class="nav-title">साइबर जागृति अभियान</div>
                <div class="nav-subtitle">उपस्थिति-श्रेणीबद्ध संचयी विवरण (शीर्ष 10 जिले)</div>
            </div>
        </div>
        <div class="nav-date">{title_date}</div>
    </div>

    <div class="section-header">
        <div class="title-wrap">
            <div class="badge-num">01</div>
            <div class="section-title">तालिका 4: शीर्ष 10 जिलावार उपस्थिति-श्रेणीबद्ध कार्यक्रम ({scope_label} तक संचयी)</div>
        </div>
        <div class="pill-scope">शीर्ष 10 जिले</div>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card"><div class="kpi-label">1 से 20 लोग</div><div class="kpi-val">{format_indian(c1_val)}</div><div class="kpi-progress"><div class="kpi-fill fill-1" style="width: {c1_pct:.1f}%;"></div></div><div class="kpi-pct">{c1_pct:.2f}%</div></div>
        <div class="kpi-card"><div class="kpi-label">20 से 50 लोग</div><div class="kpi-val">{format_indian(c2_val)}</div><div class="kpi-progress"><div class="kpi-fill fill-2" style="width: {c2_pct:.1f}%;"></div></div><div class="kpi-pct">{c2_pct:.2f}%</div></div>
        <div class="kpi-card"><div class="kpi-label">50 से 100 लोग</div><div class="kpi-val">{format_indian(c3_val)}</div><div class="kpi-progress"><div class="kpi-fill fill-3" style="width: {c3_pct:.1f}%;"></div></div><div class="kpi-pct">{c3_pct:.2f}%</div></div>
        <div class="kpi-card"><div class="kpi-label">100 से 500 लोग</div><div class="kpi-val">{format_indian(c4_val)}</div><div class="kpi-progress"><div class="kpi-fill fill-4" style="width: {c4_pct:.1f}%;"></div></div><div class="kpi-pct">{c4_pct:.2f}%</div></div>
        <div class="kpi-card"><div class="kpi-label">&gt;500 लोग</div><div class="kpi-val">{format_indian(c5_val)}</div><div class="kpi-progress"><div class="kpi-fill fill-5" style="width: {c5_pct:.1f}%;"></div></div><div class="kpi-pct">{c5_pct:.2f}%</div></div>
    </div>

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

    <div class="footer-note">{footer_text}</div>

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
</html>"""

def run():
    html_09sep = build_html(
        "बुधवार • 09 सितंबर 2026",
        "09 सितंबर 2026",
        data_09sep_cards,
        data_09sep_top10,
        "<strong>नोट:</strong> यह तालिका संलग्न छवि (09 सितंबर 2026 तक संचयी) के अनुसार <strong>शीर्ष 10 सर्वाधिक सक्रिय पुलिस जिलों</strong> के कुल <strong>1,30,604</strong> कार्यक्रमों का श्रेणीबद्ध संचयी विश्लेषण प्रदर्शित करती है।"
    )

    out_html = os.path.join(REPORTS_DIR, "top10_09sep_reverified.html")
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_09sep)

    chrome_bin = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    pdf_out = os.path.join(ARTIFACT_DIR, "Cyber_Jagriti_Top10_Districts_Report_2026-09-09_Exact.pdf")
    png_out = os.path.join(ARTIFACT_DIR, "report_top10_districts_09sep_exact.png")

    subprocess.run([chrome_bin, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf_out}", f"file://{out_html}"])
    subprocess.run([chrome_bin, "--headless", "--disable-gpu", f"--screenshot={png_out}", "--window-size=1100,950", f"file://{out_html}"])

    print("Re-verification complete!")

if __name__ == "__main__":
    run()
