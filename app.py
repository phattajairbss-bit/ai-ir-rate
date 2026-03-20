import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime

# ======================================
# Streamlit Title
# ======================================
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
    """
    ดึง IR Rate จาก Next.js Data Route ของ AIS
    """
    url = f"https://www.ais.th/_next/data/production/en/consumers/package/international/roaming/rate/{country}/{plan}/all.json"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return {"error": f"status {res.status_code}"}

        data = res.json()
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

    except Exception as e:
        return {"error": str(e)}

def run_scraper():
    """
    รัน scrape สำหรับทุก country + plan และ transform ข้อมูล
    """
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
# Streamlit Interface
# ======================================
st.subheader("🚀 AIS IR Rate Scraper")

# ปุ่มให้ผู้ใช้กดรัน
if st.button("▶️ Run Scraper Now"):
    with st.spinner("⏳ Fetching data..."):
        final_df, logs = run_scraper()

    # แสดง log
    st.subheader("🧪 Logs")
    for l in logs:
        st.text(l)

    # แสดงผลลัพธ์
    if final_df is None:
        st.error("❌ ยังไม่ได้ data → ตรวจสอบ deeper")
    else:
        st.success(f"✅ Done: {len(final_df)} rows")
        st.dataframe(final_df)

        # ดาวน์โหลด CSV
        csv = final_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download CSV",
            data=csv,
            file_name=f"ais_ir_rate_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
else:
    st.info("💡 กดปุ่ม 'Run Scraper Now' เพื่ออัปเดตข้อมูลล่าสุด")
