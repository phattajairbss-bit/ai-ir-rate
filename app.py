import streamlit as st
import pandas as pd
import requests
import json
import re
from datetime import datetime

st.title("📊 AIS IR Rate Auto Fetch (Final)")

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
    "User-Agent": "Mozilla/5.0"
}

# ======================================
# SCRAPE FUNCTION
# ======================================
def scrape_ais_rate(country, plan):

    url = f"https://www.ais.th/en/consumers/package/international/roaming/rate/{country}/{plan}/all"

    try:
        res = requests.get(url, headers=headers, timeout=15)
    except Exception as e:
        return {"error": f"request fail: {e}"}

    if res.status_code != 200:
        return {"error": f"status {res.status_code}"}

    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        res.text
    )

    if not match:
        return {"error": "no NEXT_DATA"}

    try:
        data = json.loads(match.group(1))
    except:
        return {"error": "json parse error"}

    text = json.dumps(data)

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

# ======================================
# AUTO RUN
# ======================================
st.write("🚀 Running...")

rows = []
debug_logs = []

progress = st.progress(0)

total = len(countries) * len(plans)
step = 0

for c in countries:
    for p in plans:

        step += 1

        result = scrape_ais_rate(c, p)

        if "error" in result:
            debug_logs.append(f"❌ {c}-{p}: {result['error']}")
        else:
            debug_logs.append(f"✅ {c}-{p}")
            rows.append(result)

        progress.progress(step / total)

# ======================================
# DEBUG
# ======================================
st.subheader("🧪 Debug Log")
for log in debug_logs:
    st.text(log)

if not rows:
    st.error("❌ ไม่มีข้อมูล (0 rows)")
    st.stop()

# ======================================
# RAW DATA
# ======================================
df = pd.DataFrame(rows)
st.subheader("📄 Raw Data")
st.dataframe(df)

# ======================================
# TRANSFORM
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

# ======================================
# RESULT
# ======================================
st.success(f"✅ Done: {len(final_df)} rows")
st.subheader("📊 Final Data")
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
