import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime
import schedule
import time

st.title("🔥 AIS IR Rate (API Mode - Real Fix)")

# ======================================
# CONFIG
# ======================================
countries = ["japan", "albania", "afghanistan"]
plans = ["postpaid", "prepaid"]

plan_mapping = {
    "postpaid": "sms_ir_pos",
    "prepaid": "sms_ir"
}

charge_mapping = {
    "LOCAL_CALL": ("400001021", "C_IR_MOC_VISIT"),
    "CALL_THAI": ("400001019", "C_IR_MOC_THAI"),
    "GLOBAL_CALL": ("400001020", "C_IR_MOC_3RD"),
    "RECEIVING": ("400001028", "C_IR_MTC"),
    "SMS": ("400001029", "C_IR_SMS_MO_THAI")
}

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

# ======================================
# FUNCTION: Scrape & Transform
# ======================================
def scrape_ais_rate(country, plan):
    url = f"https://www.ais.th/_next/data/production/en/consumers/package/international/roaming/rate/{country}/{plan}/all.json"
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        return {"error": f"status {res.status_code}"}

    try:
        data = res.json()
    except:
        return {"error": "json parse fail"}

    text = str(data)

    def extract(label):
        m = re.search(rf"{label}.*?([\d]+\.\d+|\d+)", text, re.IGNORECASE)
        return m.group(1) if m else None

    return {
        "COUNTRY_NAME": country.upper(),
        "SERVICE_TYPE": plan_mapping.get(plan, plan),
        "LOCAL_CALL": extract("Local"),
        "CALL_THAI": extract("Thai"),
        "GLOBAL_CALL": extract("Global"),
        "RECEIVING": extract("Receiving"),
        "SMS": extract("SMS")
    }


def run_scraper():
    rows = []
    logs = []

    for c in countries:
        for p in plans:
            result = scrape_ais_rate(c, p)

            if "error" in result:
                logs.append(f"❌ {c}-{p}: {result['error']}")
            else:
                logs.append(f"✅ {c}-{p}")
                rows.append(result)

    if not rows:
        print("❌ ยังไม่ได้ data → ตรวจสอบ deeper")
        return None, logs

    df = pd.DataFrame(rows)

    final_rows = []
    for _, row in df.iterrows():
        for rate_type, (code, name) in charge_mapping.items():
            rate = row[rate_type]
            if not rate:
                continue

            final_rows.append({
                "PROMOTION_TYPE": "normal",
                "SERVICE_TYPE": row["SERVICE_TYPE"],
                "CHARGE_CODE": code,
                "CHARGE_CODE_NAME": name,
                "RATE": rate,
                "COUNTRY_NAME": row["COUNTRY_NAME"],
                "USER_DATE": datetime.now()
            })

    final_df = pd.DataFrame(final_rows)
    return final_df, logs

# ======================================
# STREAMLIT INTERFACE
# ======================================
st.subheader("🚀 Logs / Status")
final_df, logs = run_scraper()

for l in logs:
    st.text(l)

if final_df is not None:
    st.success(f"✅ Done: {len(final_df)} rows")
    st.dataframe(final_df)

    csv = final_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download CSV",
        data=csv,
        file_name="ais_ir_rate.csv",
        mime="text/csv",
    )

# ======================================
# OPTIONAL: Scheduler (ถ้าต้องการรันอัตโนมัติ)
# ======================================
def scheduled_job():
    print("📅 Running scheduled job...")
    df, logs = run_scraper()
    if df is not None:
        df.to_csv(f"ais_ir_rate_{datetime.now().strftime('%Y%m%d')}.csv", index=False)
        print(f"✅ Saved {len(df)} rows")

# รันทุกวันจันทร์ 09:00
schedule.every().monday.at("09:00").do(scheduled_job)

# ใช้สำหรับ run บนเครื่อง server / cron alternative
# while True:
#     schedule.run_pending()
#     time.sleep(60)
