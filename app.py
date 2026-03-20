import streamlit as st
import pandas as pd
import requests
import json
import re
from datetime import datetime

st.title("📊 AIS IR Rate Auto Fetch")

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

# ======================================
# SCRAPE FUNCTION (ไม่ใช้ selenium)
# ======================================
def scrape_ais_rate(country, plan):

    url = f"https://www.ais.th/en/consumers/package/international/roaming/rate/{country}/{plan}/all"
    res = requests.get(url)

    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        res.text
    )

    if not match:
        return None

    data = json.loads(match.group(1))
    text = json.dumps(data)

    def extract(label):
        m = re.search(label + r'[^0-9]*([\d.]+)', text, re.IGNORECASE)
        return m.group(1) if m else None

    return {
        "COUNTRY_NAME": country.upper(),
        "SERVICE_TYPE": plan_mapping.get(plan, plan),
        "LOCAL_CALL": extract("Local Call"),
        "CALL_THAI": extract("Call to Thai"),
        "GLOBAL_CALL": extract("Global Call"),
        "RECEIVING": extract("Receiving"),
        "SMS": extract("SMS")
    }

# ======================================
# MAIN BUTTON
# ======================================
if st.button("🚀 Run ทั้งหมด"):

    rows = []

    progress = st.progress(0)

    for i, c in enumerate(countries):
        for p in plans:
            try:
                result = scrape_ais_rate(c, p)
                if result:
                    rows.append(result)
            except Exception as e:
                st.error(f"Error {c}-{p}: {e}")

        progress.progress((i + 1) / len(countries))

    df = pd.DataFrame(rows)

    # ======================================
    # TRANSFORM FORMAT
    # ======================================
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

    st.success(f"✅ Done: {len(final_df)} rows")
    st.dataframe(final_df)

    # ======================================
    # DOWNLOAD CSV
    # ======================================
    csv = final_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "📥 Download CSV",
        data=csv,
        file_name="ais_ir_rate.csv",
        mime="text/csv",
    )
