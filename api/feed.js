// Vercel Serverless Edge API Function: /api/feed
// Fetches real-time Cyber Jagriti metrics from the police portal with CORS and 5s edge caching

let cachedToken = null;
let tokenExpiresAt = 0;

async function getAuthToken() {
  const now = Date.now();
  if (cachedToken && now < tokenExpiresAt) {
    return cachedToken;
  }

  const res = await fetch("https://cyberjagriti.policemitanrpr.com/api/login/check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: "admin", ***REMOVED***: "***REMOVED***" })
  });

  if (!res.ok) {
    throw new Error("Police portal auth failed: " + res.status);
  }

  const data = await res.json();
  cachedToken = data.token;
  tokenExpiresAt = now + 4 * 3600 * 1000; // Cache for 4 hours
  return cachedToken;
}

export default async function handler(req, res) {
  // Enable full cross-origin resource sharing
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");

  if (req.method === "OPTIONS") {
    return res.status(200).end();
  }

  // 5-second edge cache: fast enough to be live, protected against DDoS
  res.setHeader("Cache-Control", "public, s-maxage=5, stale-while-revalidate=5");

  try {
    const token = await getAuthToken();
    const dashRes = await fetch("https://cyberjagriti.policemitanrpr.com/api/cyber_crime/dashboard", {
      headers: {
        "Authorization": token,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json"
      }
    });

    if (!dashRes.ok) {
      throw new Error("Portal dashboard error: " + dashRes.status);
    }

    const data = await dashRes.json();
    const counter = data.counter || {};
    const totalEvents = parseInt(counter.total_entries || 0);
    const totalReach = parseInt(counter.total_members || 0);
    const avgAttendance = totalEvents > 0 ? parseFloat((totalReach / totalEvents).toFixed(1)) : 0;

    let raipurEvents = 0;
    let raipurReach = 0;
    const districtsMap = new Map();

    (data.districts || []).forEach(d => {
      const did = parseInt(d.district_id);
      const ev = parseInt(d.total || 0);
      const rch = parseInt(d.total_members || 0);
      if (did === 27 || did === 34) {
        raipurEvents += ev;
        raipurReach += rch;
      } else {
        districtsMap.set(did, {
          id: did,
          name_en: d.district_name_en,
          name_hi: d.district_name_hi,
          events: ev,
          reach: rch,
          avg_attendance: ev > 0 ? parseFloat((rch / ev).toFixed(1)) : 0
        });
      }
    });

    districtsMap.set(27, {
      id: 27,
      name_en: "Raipur",
      name_hi: "रायपुर",
      events: raipurEvents,
      reach: raipurReach,
      avg_attendance: raipurEvents > 0 ? parseFloat((raipurReach / raipurEvents).toFixed(1)) : 0
    });

    const districts = Array.from(districtsMap.values()).sort((a, b) => b.events - a.events);
    districts.forEach((d, idx) => { d.rank = idx + 1; });

    return res.status(200).json({
      status: "LIVE_EDGE",
      timestamp: new Date().toISOString(),
      total_events: totalEvents,
      total_reach: totalReach,
      avg_attendance: avgAttendance,
      districts_count: districts.length,
      districts: districts
    });
  } catch (error) {
    return res.status(500).json({
      status: "ERROR",
      message: error.message
    });
  }
}
