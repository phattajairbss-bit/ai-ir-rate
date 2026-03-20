import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime

st.title("🔥 AIS IR Rate Scraper (HTML + Regex Multi-line)")

# ======================================
# CONFIG
# ======================================
countries = [
    "afghanistan",
    "albania",
    "algeria",
    "japan",
    "thailand",
    "singapore"
]
plans = ["prepaid", "postpaid"]

plan_mapping = {
    "postpaid": "sms_ir_pos",
    "prepaid": "sms_ir"
}

# Charge code mapping
charge_mapping = {
    "LOCAL_CALL": ("400001021", "C_IR_MOC_VISIT"),
    "CALL_THAI": ("400001019", "C_IR_MOC_THAI"),
    "GLOBAL_CALL": ("400001020", "C_IR_MOC_3RD"),
    "RECEIVING": ("400001028", "C_IR_MTC"),
    "SMS": ("400001029", "C_IR_SMS_MO_THAI"),
    "DATA": ("400001030", "C_IR_DATA_ROAMING")
}

# ======================================
# FUNCTION: Scrape HTML text and parse rates
# ======================================
def scrape_rates(country_slug, plan):
    url = f"https://www.ais.th/en/consumers/package/international/roaming/rate/{country_slug}/{plan}/all"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code != 200:
            return {"error": f"status {res.status_code}"}

        text = res.text

        # Regex patterns for multi-line rates
        patterns = {
            "LOCAL_CALL": r"Local Call\s*\n\s*([\d.]+)",
            "CALL_THAI": r"Call to Thai\s*\n\s*([\d.]+)",
            "GLOBAL_CALL": r"Global call\s*\n\s*([\d.]+)",
            "RECEIVING": r"Receiving calls\s*\n\s*([\d.]+)",
            "SMS": r"SMS Roaming\s*\n\s*([\d.]+)",
            "DATA": r"Data roaming\s*\n\s*([\d.]+)"
        }

        rates = {}
        for key, pat in patterns.items():
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                rates[key] = float(m.group(1))

        if not rates:
            return {"error": "No rates found"}

        # Add meta info
        rates["COUNTRY_NAME"] = country_slug.upper()
        rates["SERVICE_TYPE"] = plan_mapping.get(plan, plan)

        return rates

    except Exception as e:
        return {"error": str(e)}

# ======================================
# STREAMLIT INTERFACE
# ======================================
st.subheader("🚀 AIS IR Rate Scraper")

if st.button("▶️ Run Scraper Now"):

    all_rows = []
    logs = []

    for c in countries:
        for p in plans:
            st.text(f"Scraping {c.upper()} - {p}")
            result = scrape_rates(c, p)
            if "error" in result:
                logs.append(f"❌ {c}-{p}: {result['error']}")
            else:
                logs.append(f"✅ {c}-{p}")
                # Transform to CHARGE_CODE format
                for rate_type, (code, name) in charge_mapping.items():
                    if rate_type in result:
                        all_rows.append({
                            "PROMOTION_TYPE": "normal",
                            "SERVICE_TYPE": result["SERVICE_TYPE"],
                            "CHARGE_CODE": code,
                            "CHARGE_CODE_NAME": name,
                            "RATE": result[rate_type],
                            "COUNTRY_NAME": result["COUNTRY_NAME"],
                            "USER_DATE": datetime.now()
                        })

    # Logs
    st.subheader("🧪 Logs")
    for l in logs:
        st.text(l)

    # Combine all
    if all_rows:
        combined_df = pd.DataFrame(all_rows)
        st.success(f"✅ Done: {len(combined_df)} rows")
        st.dataframe(combined_df)

        # Download CSV
        csv = combined_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download CSV",
            data=csv,
            file_name=f"ais_ir_rate_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.error("❌ ยังไม่ได้ data")

else:
    st.info("💡 กดปุ่ม 'Run Scraper Now' เพื่ออัปเดตข้อมูลล่าสุด")
