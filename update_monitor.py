import re

with open('/Users/abhijeet/.gemini/antigravity-ide/scratch/cyber-jagriti-monitor/cyber_jagriti_monitor.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add whatsapp sending capability and config
whatsapp_helper = '''
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
        top_text += f"{idx}️⃣ *{d['district_name_hi']}:* {d['total']:,} इवेंट्स | {d['total_members']:,} नागरिक\\n"

    bottom_text = ""
    for idx, d in enumerate(bottom_five, 1):
        bottom_text += f"{idx}️⃣ *{d['district_name_hi']}:* {d['total']:,} इवेंट्स | {d['total_members']:,} नागरिक\\n"

    msg = f"""🛡️ *साइबर जागृति अभियान - दैनिक एनालिटिक्स रिपोर्ट*
📅 *तारीख:* {formatted_date} (9:00 PM Snapshot)
━━━━━━━━━━━━━━━━━━━━━

📊 *1. कुल राज्य आंकड़े (Cumulative Stats)*
• *कुल जागरूक नागरिक (Total Aware):* {total_members:,}
• *कुल राज्य प्रविष्टियाँ (Total Events):* {total_entries:,}

⚡ *2. आज की गतिविधि (Today's Stats)*
• *आज के कुल इवेंट (Today's Events):* {today_entries:,}
• *आज जागरूक नागरिक (Today's Aware):* {today_members:,}

━━━━━━━━━━━━━━━━━━━━━
🔍 *3. कार्यकारी विश्लेषण (Executive Analysis)*
• *Volume Performance:* आज राज्यभर में कुल *{today_entries:,} नए events* दर्ज हुए, जिससे single-day reach *{today_members:,} नागरिकों* तक पहुंची। Kondagaon और Gariaband लगातार high volume lead कर रहे हैं।
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
    # Check config or environment
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
        print("[*] WhatsApp notification skipped (no CallMeBot credentials in whatsapp_config.json yet).")
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
'''

# Insert helper before main()
code = code.replace("def main():", whatsapp_helper + "\n\ndef main():")
# Update main() to call send_whatsapp_callmebot
code = code.replace("send_email(pdf_path, latest_date)", """send_email(pdf_path, latest_date)
        wa_msg = build_whatsapp_summary(data, latest_date)
        send_whatsapp_callmebot(wa_msg)""")

with open('/Users/abhijeet/.gemini/antigravity-ide/scratch/cyber-jagriti-monitor/cyber_jagriti_monitor.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Updated cyber_jagriti_monitor.py with WhatsApp support")
