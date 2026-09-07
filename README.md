# 🛡️ छत्तीसगढ़ पुलिस | साइबर जागृति अभियान — Geospatial Impact Dashboard

[![Live Geospatial Map](https://img.shields.io/badge/LIVE_MAP-Online_Portal-red?style=for-the-badge&logo=googlemaps)](https://kodanda10.github.io/chhattisgarh-cyber-jagriti-map/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)
[![Automated Sync](https://img.shields.io/badge/Sync-Every_15_mins-emerald?style=for-the-badge&logo=githubactions)](.github/workflows/live_sync.yml)

An executive-grade, mobile-responsive geospatial intelligence dashboard visualizing the reach and ground-level awareness impact across all **33 administrative districts** and frontline police station hubs (*थाना केंद्र*) in Chhattisgarh under the statewide **साइबर जागृति अभियान** (Cyber Awareness Campaign).

🔗 **Live Public Dashboard**: [https://kodanda10.github.io/chhattisgarh-cyber-jagriti-map/](https://kodanda10.github.io/chhattisgarh-cyber-jagriti-map/)

---

## 🌟 Key Highlights & Features

1. **High-Contrast Choropleth Mapping**:
   - 5 vibrant, distinct density tiers (Azure Blue `>10k`, Electric Purple `5k–10k`, Emerald Green `1k–5k`, Vivid Amber `500–1k`, Crimson Rose `<500`).
   - Official Devanagari district typography with razor-sharp administrative boundaries.
   - Frontline Thana Hub markers with interactive impact tooltips.

2. **Real-Time Mechanical Rolling Odometer**:
   - Dynamic odometer roll with precision cubic ease-out.
   - **Emerald Green Glow** (`#22c55e`) during active data changes, settling smoothly to native typography.
   - Seamless cross-surface synchronization across Header KPIs, Mobile Telemetry Strip, District Ranking Cards, and Slide-over Inspector.

3. **Mobile-First Responsive Experience**:
   - 100% viewport interactive Leaflet map on all smartphones and tablets.
   - Micro-telemetry summary strip docked beneath the slim header.
   - Native Bottom Sheet Drawer (`[ ☰ 33 जिलों की रैंकिंग ▲ ]`) with drag handle, quick search, and filter pills.
   - Bottom Sheet Deep-Dive Inspector modal with full thana and focus topic analytics.

4. **Automated Zero-Database Cloud Sync**:
   - Powered by GitHub Actions scheduled every 15 minutes.
   - Fetches live deltas directly from the Chhattisgarh Police Cyber Crime portal.
   - Updates `live_feed.json` (53 KB) with zero database overhead.

---

## 📊 State Telemetry Overview

- **Districts Covered**: 33 / 33 Administrative Districts (100% Coverage)
- **Top District**: गरियाबंद (Gariaband) & कोंडागांव (Kondagaon)
- **Live Sync Cadence**: Every 15 minutes via GitHub Actions

---

## 🛠️ Local Development

```bash
# 1. Clone the repository
git clone https://github.com/Kodanda10/chhattisgarh-cyber-jagriti-map.git
cd chhattisgarh-cyber-jagriti-map

# 2. Start a local HTTP server
python3 -m http.server 8080

# 3. Open in browser
open http://localhost:8080/index.html
```

---

*छत्तीसगढ़ पुलिस — साइबर सुरक्षित छत्तीसगढ़ संकल्प*
