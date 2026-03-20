import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ======================================
st.title("🔥 AIS IR Rate Scraper (JSON Endpoint)")

# CONFIG
countries = ["japan", "thailand", "singapore"]
plans = ["postpaid", "prepaid"]

# CHARGE_CODE mapping
charge_mapping = {
    "Local": ("400001021", "C_IR_MOC_VISIT"),
    "Call Thai": ("400001019", "C_IR_MOC_THAI"),
    "Global": ("400001020", "C_IR_MOC_3RD"),
    "Receiving": ("400001028", "C_IR_MTC"),
    "SMS": ("400001029", "C_IR_SMS_MO_THAI"),
}

# ======================================
# FUNCTION: Scrape JSON from Next.js endpoint
def scrape_ais_json(country, plan):
    url = f"https://www.ais.th/_next/data/production/en/consumers/package/international/roaming/rate/{country}/{plan}/all.json"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return {"error": f"status {res.status_code}"}

        data = res.json()

        # ดึง rates จาก JSON
        rates = {}
        text = str(data)
        for key in charge_mapping.keys():
            import re
            m = re.search(rf"{key}.*?([\d]+\.\d+|\d+)", text, re.IGNORECASE)
            rates[key] = m.group(1) if m else None

        return {
            "COUNTRY_NAME": country.upper(),
            "SERVICE_TYPE": plan,
            **rates
        }

    except Exception as e:
        return {"error": str(e)}

# ======================================
# FUNCTION: Transform JSON → DataFrame
def transform_json(df_rows):
    final_rows = []
    for row in df_rows:
        for key, (code, name) in charge_mapping.items():
            rate = row.get(key)
            if rate is None:
                continue
            final_rows.append({
                "PROMOTION_TYPE": "normal",
                "SERVICE_TYPE": row["SERVICE_TYPE"],
                "CHARGE_CODE": code,
                "CHARGE_CODE_NAME": name,
                "RATE": float(rate),
                "COUNTRY_NAME": row["COUNTRY_NAME"],
                "USER_DATE": datetime.now()
            })
    return pd.DataFrame(final_rows)

# ======================================
# Streamlit Interface
st.subheader("🚀 AIS IR Rate Scraper (JSON Endpoint)")

if st.button("▶️ Run Scraper Now"):
    rows = []
    logs = []

    for c in countries:
        for p in plans:
            result = scrape_ais_json(c, p)
            if "error" in result:
                logs.append(f"❌ {c}-{p}: {result['error']}")
            else:
                logs.append(f"✅ {c}-{p}")
                rows.append(result)

    # Logs
    st.subheader("🧪 Logs")
    for l in logs:
        st.text(l)

    # Transform & Combine
    if rows:
        final_df = transform_json(rows)
        st.success(f"✅ Done: {len(final_df)} rows")
        st.dataframe(final_df)

        # Download CSV
        csv = final_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download CSV",
            data=csv,
            file_name=f"ais_ir_rate_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.error("❌ ยังไม่ได้ data → ตรวจสอบ deeper")
else:
    st.info("💡 กดปุ่ม 'Run Scraper Now' เพื่ออัปเดตข้อมูลล่าสุด")
